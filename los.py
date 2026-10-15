import asyncio
import json
import os
import random
from datetime import datetime
from telethon import TelegramClient, events, errors
from telethon.tl.types import Channel, Chat, User, Message

# ------------------ إعدادات الحساب ------------------
API_ID = 37339814
API_HASH = 'ae48a0532f231876e98751b21263ae26'

client = TelegramClient('session_name', API_ID, API_HASH)

DATA_FILE = "script_data.json"
INSULTS_DB_FILE = "insults_db.json"

XLR_RIGHTS = "𝗫𝗟𝗥 𝗦𝗼𝘂𝗿𝗰𝗲 | @rlor1"

active_bombings = {}
muted_private = set()
muted_group = set()
paused = False
current_category = "مفرداتي"
targets_info = {}
lines_per_message = 3

# ------------------ قاعدة البيانات ------------------
def load_insults_db():
    if os.path.exists(INSULTS_DB_FILE):
        with open(INSULTS_DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        default_lines = [
            "ابن سيكوباثيه ابن المجرمه ابن الزنجيه ابن العنتيله",
            "ابن الدبه القحبه ابن الكلبه الامريكيه ابن المنيوكه السافله",
            "ابن القحبانيه ابن الاغريقيه ابن السافله ابن الكافره",
            "ابن الزنديق ابن البوذيه ابن الوحشيه ابن الكلبانيه",
            "يخو المنيوكييه يبن المطروحه انيك والدينك يبن حماره",
            "انيك قبيلتك ي ديوث انيك ميجار اهلك انيك ميجار امك",
            "انيك امك القحبه انيك اختك الزانيه انيك امك الواشيه",
            "انكح امك الخياطه انيك امك هيه زعلانه انيك امك ب غرفت ابوك",
            "يابن المتلطمه يابن ليبراليه يابن المحروقه يابن المنكوحه",
            "كس امك بجزمتي يابن الايرانديه يابن الخليجيه يابن البابليه",
            "يابن الفرعونيه يابن الجزمه يابن النعال يابن القندرا",
            "يابن الديموراطيه يابن المليوصه يابن البربوصه يابن المعموصه",
            "يابن المتفشله يابن المستعبده يابن الجلوخيه يابن السكساويه",
            "يابن الممزوغ يابن الغوله يابن الشنوطيه يابن المطقوق",
            "يابن المكسورا يابن الفاسقه يابن الحبشيه يابن الفارسيه",
            "يابن الامازيغيه يابن الغجريه يابن الشوعيه يابن النازيه",
            "يابن السوفيتيه يابن المتفجره يخو المنفلقه يخو المفقحه",
            "يخو المبقعه يخو المنيوكييه يبن المطروحه"
        ]
        default_db = {"مفرداتي": default_lines}
        with open(INSULTS_DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(default_db, f, ensure_ascii=False, indent=4)
        return default_db

insults_db = load_insults_db()

def get_distinct_lines(n):
    lines = data["lines"]
    if not lines:
        return ""
    if len(lines) < n:
        return " ".join(lines)
    return " ".join(random.sample(lines, n))

# ------------------ بيانات التحكم ------------------
data = {
    "is_running": True,
    "delay": 0.0,
    "target_users": set(),
    "lines": insults_db.get(current_category, []),
    "current_index": 0,
    "locks": {}
}

def save_data():
    save_dict = {
        "is_running": data["is_running"],
        "delay": data["delay"],
        "target_users": list(data["target_users"]),
        "current_index": data["current_index"],
        "current_category": current_category
    }
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(save_dict, f, ensure_ascii=False, indent=4)

def load_data():
    default_data = {"is_running": True, "delay": 0.0, "target_users": [],
                    "current_index": 0, "current_category": "مفرداتي"}
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            try:
                loaded = json.load(f)
                loaded["target_users"] = set(loaded.get("target_users", []))
                return loaded
            except:
                return default_data
    return default_data

loaded_config = load_data()
data.update(loaded_config)
current_category = loaded_config.get("current_category", "مفرداتي")
data["lines"] = insults_db.get(current_category, [])

# ------------------ دالة الحصول على الهدف ------------------
async def get_target(event, target_input=None):
    if event.is_reply and not target_input:
        reply = await event.get_reply_message()
        sender = await reply.get_sender()
        target_id = sender.id
        target_name = f"@{sender.username}" if sender.username else str(sender.id)
        return target_id, target_name, None
    if target_input:
        target_input = target_input.strip()
        try:
            if target_input.isdigit() or (target_input.startswith('-') and target_input[1:].isdigit()):
                target_id = int(target_input)
                target_name = str(target_id)
            else:
                entity = await client.get_entity(target_input)
                target_id = entity.id
                target_name = f"@{entity.username}" if entity.username else str(entity.id)
            return target_id, target_name, None
        except Exception as e:
            return None, None, f"❌ خطأ: {e}"
    return None, None, "⚠️ حدد الهدف"

# ============================================================
#  1. مهمة التفجير العادي (ردود في القروب)
# ============================================================
async def bombing_task(target_id, target_name, chat_id, reply_to_msg_id, is_private, mention=False):
    global paused
    if not data["lines"]:
        return
    target_messages = []
    if not is_private and reply_to_msg_id:
        try:
            msgs = await client.get_messages(chat_id, limit=10, from_user=target_id)
            target_messages = [m.id for m in msgs if m]
            if not target_messages:
                target_messages = [reply_to_msg_id]
        except:
            target_messages = [reply_to_msg_id] if reply_to_msg_id else []
    msg_update_counter = 0

    while target_id in active_bombings and data["is_running"]:
        if paused:
            await asyncio.sleep(0.1)
            continue
        text = get_distinct_lines(lines_per_message)
        if mention and not is_private:
            text = f"@{target_name} {text}"
        try:
            if is_private:
                await client.send_message(chat_id, text)
            else:
                current_reply = random.choice(target_messages) if target_messages else reply_to_msg_id
                msg_update_counter += 1
                if msg_update_counter >= 5:
                    try:
                        msgs = await client.get_messages(chat_id, limit=10, from_user=target_id)
                        new_ids = [m.id for m in msgs if m]
                        if new_ids:
                            target_messages = new_ids
                        msg_update_counter = 0
                    except:
                        pass
                await client.send_message(chat_id, text, reply_to=current_reply)
            await asyncio.sleep(data["delay"])
        except errors.FloodWaitError as e:
            await asyncio.sleep(e.seconds + 1)
        except Exception:
            await asyncio.sleep(0.3)

    if target_id in active_bombings:
        del active_bombings[target_id]

# ============================================================
#  2. مهمة المنشن المستمر (تفو) - تفجير بالمنشن في loop
# ============================================================
async def mention_loop_task(target_id, target_name, chat_id):
    global paused
    if not data["lines"]:
        return
    # نبحث عن قروب مشترك إذا لم يُحدد
    if not chat_id:
        async for dialog in client.iter_dialogs(limit=30):
            if dialog.is_group:
                async for m in client.iter_messages(dialog.id, limit=20, from_user=target_id):
                    chat_id = dialog.id
                    break
            if chat_id:
                break
        if not chat_id:
            await client.send_message('me', f"❌ لا يوجد قروب مشترك مع {target_name}")
            if target_id in active_bombings:
                del active_bombings[target_id]
            return

    while target_id in active_bombings and data["is_running"]:
        if paused:
            await asyncio.sleep(0.1)
            continue
        try:
            text = get_distinct_lines(lines_per_message)
            final_text = f"@{target_name} {text}"
            await client.send_message(chat_id, final_text)
            await asyncio.sleep(data["delay"])
        except errors.FloodWaitError as e:
            await asyncio.sleep(e.seconds + 1)
        except Exception:
            await asyncio.sleep(0.3)

    if target_id in active_bombings:
        del active_bombings[target_id]

# ============================================================
#  3. مهمة الرد التلقائي في الخاص (تف) - يرد على رسائل الشخص
# ============================================================
async def private_reply_task(target_id, target_name):
    global paused
    if not data["lines"]:
        return
    processed_msgs = set()
    while target_id in active_bombings and data["is_running"]:
        if paused:
            await asyncio.sleep(0.1)
            continue
        try:
            async for msg in client.iter_messages(target_id, limit=15, from_user=target_id):
                if msg.id in processed_msgs:
                    continue
                text = get_distinct_lines(lines_per_message)
                try:
                    await client.send_message(target_id, text, reply_to=msg.id)
                    processed_msgs.add(msg.id)
                    await asyncio.sleep(data["delay"])
                except errors.FloodWaitError as e:
                    await asyncio.sleep(e.seconds + 1)
                except Exception:
                    pass
            if len(processed_msgs) > 500:
                processed_msgs = set(list(processed_msgs)[-500:])
        except Exception:
            pass
        await asyncio.sleep(1)

    if target_id in active_bombings:
        del active_bombings[target_id]

# ============================================================
#  4. مهمة السبام المخصص (سبام [عدد] [كلمة])
# ============================================================
async def custom_spam_task(target_id, chat_id, is_private, count, word):
    for _ in range(count):
        if not data["is_running"] or target_id not in active_bombings:
            break
        if paused:
            await asyncio.sleep(0.1)
            continue
        try:
            await client.send_message(chat_id, word)
            await asyncio.sleep(data["delay"])
        except errors.FloodWaitError as e:
            await asyncio.sleep(e.seconds + 1)
        except Exception:
            await asyncio.sleep(0.3)
    if target_id in active_bombings:
        del active_bombings[target_id]

# ------------------ دالة بدء التفجير ------------------
async def start_attack(event, attack_type, target_input=None, spam_count=None, custom_word=None):
    global paused
    if not data["is_running"]:
        await client.send_message('me', "⚠️ السكربت متوقف")
        return
    if paused:
        await client.send_message('me', "⚠️ الأوامر موقوفة")
        return

    target_id, target_name, err = await get_target(event, target_input)
    if err:
        await client.send_message('me', err)
        return

    if target_id in active_bombings:
        await client.send_message('me', f"⚠️ {target_name} قيد النيك بالفعل")
        return

    # ====== حالات خاصة ======
    if attack_type == 'mention_loop':
        # تفو - منشن مستمر
        chat_id = None
        task = asyncio.create_task(mention_loop_task(target_id, target_name, chat_id))
        active_bombings[target_id] = task
        await client.send_message('me', f"🔥 بدأ المنشن المستمر على {target_name}")
        return

    if attack_type == 'private_reply':
        # تف - ردود على رسائل الخاص
        task = asyncio.create_task(private_reply_task(target_id, target_name))
        active_bombings[target_id] = task
        await client.send_message('me', f"🔥 بدأ الرد على رسائل {target_name} في الخاص")
        return

    if attack_type == 'custom_spam':
        # سبام [عدد] [كلمة]
        if not custom_word:
            await client.send_message('me', "⚠️ اكتب: `.سبام [عدد] [كلمة]`")
            return
        count = spam_count or 10
        is_private = event.is_private
        chat_id = target_id if is_private else None
        if not is_private:
            async for dialog in client.iter_dialogs(limit=25):
                if dialog.is_group:
                    chat_id = dialog.id
                    break
        if not chat_id:
            await client.send_message('me', "❌ لم يتم العثور على قروب/خاص")
            return
        task = asyncio.create_task(custom_spam_task(target_id, chat_id, is_private, count, custom_word))
        active_bombings[target_id] = task
        await client.send_message('me', f"🔥 سبام '{custom_word}' ×{count} على {target_name}")
        return

    # ====== التفجير العادي ======
    if not data["lines"]:
        await client.send_message('me', "⚠️ لا توجد سطور")
        return

    is_private = False
    reply_needed = False
    mention = False

    if attack_type == 'private':
        is_private = True
    elif attack_type == 'group':
        is_private = False
        reply_needed = True
    elif attack_type == 'group_mention':
        is_private = False
        reply_needed = True
        mention = True
    elif attack_type == 'group_noreply':
        is_private = False
        reply_needed = False

    found_msg_id = None
    chat_id = None

    if not is_private:
        if reply_needed:
            async for dialog in client.iter_dialogs(limit=25):
                if dialog.is_group:
                    async for m in client.iter_messages(dialog.id, limit=30, from_user=target_id):
                        found_msg_id = m.id
                        chat_id = dialog.id
                        break
                if found_msg_id:
                    break
            if not found_msg_id:
                await client.send_message('me', f"❌ لا توجد رسائل للهدف {target_name}")
                return
        else:
            async for dialog in client.iter_dialogs(limit=25):
                if dialog.is_group:
                    chat_id = dialog.id
                    break
            if not chat_id:
                await client.send_message('me', f"❌ لا يوجد قروب مشترك")
                return
    else:
        chat_id = target_id

    task = asyncio.create_task(bombing_task(target_id, target_name, chat_id,
                                            found_msg_id if reply_needed else None,
                                            is_private, mention))
    active_bombings[target_id] = task
    await client.send_message('me', f"🔥 جاري نيك {target_name} 🔥")

# ============================================================
#                     الأوامر
# ============================================================

# تفجير عادي
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.توف(?:\s+(.+))?$'))
async def cmd_twf(event):
    await start_attack(event, 'group', event.pattern_match.group(1))

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.همم(?:\s+(.+))?$'))
async def cmd_hmm(event):
    await start_attack(event, 'group_noreply', event.pattern_match.group(1))

# تف = ردود على رسائل الخاص
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.تف(?:\s+(.+))?$'))
async def cmd_tf(event):
    await start_attack(event, 'private_reply', event.pattern_match.group(1))

# تفو = منشن مستمر
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.تفو(?:\s+(.+))?$'))
async def cmd_tfo(event):
    await start_attack(event, 'mention_loop', event.pattern_match.group(1))

# سبام [عدد] [كلمة]
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.سبام (\d+)\s+(.+)$'))
async def cmd_spam(event):
    count = int(event.pattern_match.group(1))
    word = event.pattern_match.group(2).strip()
    await start_attack(event, 'custom_spam', None, count, word)

# ------------------ ضبط الوقت ------------------
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.وقت (\d+(?:\.\d+)?)$'))
async def set_time_delay(event):
    await event.delete()
    val = float(event.pattern_match.group(1))
    data["delay"] = val
    save_data()
    await client.send_message('me', f"⏳ التأخير: {val} ثانية")

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.سريع$'))
async def set_fast(event):
    await event.delete()
    data["delay"] = 0.0
    save_data()
    await client.send_message('me', "⚡ سرعة خارقة (0 ث)")

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.بطيء$'))
async def set_slow(event):
    await event.delete()
    data["delay"] = 2
    save_data()
    await client.send_message('me', "🐢 سرعة عادية (2 ث)")

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.عدد السطور (\d+)$'))
async def set_lines(event):
    await event.delete()
    global lines_per_message
    val = int(event.pattern_match.group(1))
    if val < 1:
        await client.send_message('me', "⚠️ العدد 1 على الأقل")
        return
    lines_per_message = val
    await client.send_message('me', f"📄 عدد الأسطر: {val}")

# ------------------ نقطة الإيقاف (Toggle سليم) ------------------
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.$'))
async def dot_pause(event):
    await event.delete()
    global paused
    paused = not paused
    if paused:
        await client.send_message('me', "⏸️ **تم الإيقاف المؤقت** - المهام متوقفة (لا تُحذف)")
    else:
        await client.send_message('me', "▶️ **تم الاستئناف** - المهام استمرت")

# ------------------ قاعدة السطور ------------------
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.قاعده$'))
async def show_full_db(event):
    await event.delete()
    total = sum(len(v) for v in insults_db.values())
    msg = f"**📚 قاعدة البيانات الكاملة**\n"
    msg += f"**عدد التصنيفات:** {len(insults_db)}\n"
    msg += f"**إجمالي السطور:** {total}\n"
    msg += f"**التصنيف الحالي:** {current_category}\n\n"
    for cat, lines in insults_db.items():
        msg += f"**━━━ 📂 {cat} ({len(lines)} سطر) ━━━**\n"
        for i, line in enumerate(lines, 1):
            msg += f"`{i}.` {line}\n"
        msg += "\n"
        # تقسيم الرسالة إذا طالت
        if len(msg) > 3800:
            await client.send_message('me', msg)
            msg = ""
    if msg:
        await client.send_message('me', msg)

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.قاعده (.+)$'))
async def show_cat_db(event):
    await event.delete()
    cat = event.pattern_match.group(1).strip()
    if cat not in insults_db:
        await client.send_message('me', f"❌ التصنيف '{cat}' غير موجود")
        return
    lines = insults_db[cat]
    msg = f"**📂 {cat} ({len(lines)} سطر)**\n\n"
    for i, line in enumerate(lines, 1):
        msg += f"`{i}.` {line}\n"
        if len(msg) > 3800:
            await client.send_message('me', msg)
            msg = ""
    if msg:
        await client.send_message('me', msg)

# ------------------ إدارة قاعدة البيانات ------------------
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.تصنيفات$'))
async def list_cats(event):
    await event.delete()
    msg = "**📂 التصنيفات:**\n"
    for i, cat in enumerate(insults_db.keys(), 1):
        msg += f"{i}. {cat} ({len(insults_db[cat])} سطر)\n"
    msg += f"\n**الحالي:** {current_category}"
    await client.send_message('me', msg)

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.تصنيف (.+)$'))
async def change_cat(event):
    await event.delete()
    cat = event.pattern_match.group(1).strip()
    if cat in insults_db:
        global current_category
        current_category = cat
        data["lines"] = insults_db[cat]
        save_data()
        await client.send_message('me', f"✅ التصنيف: **{cat}** ({len(data['lines'])} سطر)")
    else:
        await client.send_message('me', "❌ التصنيف غير موجود")

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.رد$'))
async def add_lines(event):
    await event.delete()
    if event.is_reply:
        reply = await event.get_reply_message()
        new_lines = [l.strip() for l in reply.text.split('\n') if l.strip()]
        for line in new_lines:
            if line not in insults_db[current_category]:
                insults_db[current_category].append(line)
        data["lines"] = insults_db[current_category]
        with open(INSULTS_DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(insults_db, f, ensure_ascii=False, indent=4)
        save_data()
        await client.send_message('me', f"✅ تم حفظ {len(new_lines)} سطر. الإجمالي: {len(data['lines'])}")
    else:
        await client.send_message('me', "⚠️ رد على النص بـ .رد")

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.مسح السطور$'))
async def clear_lines(event):
    await event.delete()
    insults_db[current_category] = []
    data["lines"] = []
    with open(INSULTS_DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(insults_db, f, ensure_ascii=False, indent=4)
    save_data()
    await client.send_message('me', f"🗑 تم مسح سطور '{current_category}'")

# ------------------ الكتم ------------------
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.كتم خاص(?:\s+(.+))?$'))
async def mute_private_cmd(event):
    await event.delete()
    ti = event.pattern_match.group(1)
    if ti:
        tid, tname, err = await get_target(event, ti)
        if err:
            await client.send_message('me', err); return
        muted_private.add(tid)
        await client.send_message('me', f"🔇 تم كتم {tname}")
    elif event.is_reply:
        r = await event.get_reply_message()
        s = await r.get_sender()
        muted_private.add(s.id)
        await client.send_message('me', f"🔇 تم كتم {s.id}")

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.الغاء كتم خاص(?:\s+(.+))?$'))
async def unmute_private_cmd(event):
    await event.delete()
    ti = event.pattern_match.group(1)
    if ti:
        tid, tname, err = await get_target(event, ti)
        if err:
            await client.send_message('me', err); return
        muted_private.discard(tid)
        await client.send_message('me', f"🔊 تم إلغاء الكتم عن {tname}")

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.كتم قروب(?:\s+(.+))?$'))
async def mute_group_cmd(event):
    await event.delete()
    ti = event.pattern_match.group(1)
    if ti:
        tid, tname, err = await get_target(event, ti)
        if err:
            await client.send_message('me', err); return
        muted_group.add(tid)
        await client.send_message('me', f"🔇 تم كتم {tname} في القروبات")
    elif event.is_reply:
        r = await event.get_reply_message()
        s = await r.get_sender()
        muted_group.add(s.id)
        await client.send_message('me', f"🔇 تم كتم {s.id}")

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.الغاء كتم قروب(?:\s+(.+))?$'))
async def unmute_group_cmd(event):
    await event.delete()
    ti = event.pattern_match.group(1)
    if ti:
        tid, tname, err = await get_target(event, ti)
        if err:
            await client.send_message('me', err); return
        muted_group.discard(tid)
        await client.send_message('me', f"🔊 تم إلغاء الكتم عن {tname}")

# ------------------ أوامر عامة ------------------
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.تشغيل$'))
async def start_global(event):
    await event.delete()
    global paused
    data["is_running"] = True
    paused = False
    save_data()
    await client.send_message('me', "▶️ تم تشغيل السكربت")

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.توقف$'))
async def stop_global(event):
    await event.delete()
    for t in active_bombings.values():
        t.cancel()
    active_bombings.clear()
    data["is_running"] = False
    save_data()
    await client.send_message('me', "🛑 تم إيقاف السكربت")

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.تصفير$'))
async def clear_all(event):
    await event.delete()
    for t in active_bombings.values():
        t.cancel()
    active_bombings.clear()
    data["target_users"].clear()
    save_data()
    await client.send_message('me', "🛑 تم الإيقاف الكامل")

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.ايقاف الكل$'))
async def stop_all_tasks(event):
    await event.delete()
    for t in active_bombings.values():
        t.cancel()
    active_bombings.clear()
    await client.send_message('me', "🛑 تم إيقاف كل المهام النشطة")

# ------------------ طرد ------------------
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.طرد (.+)$'))
async def target_cmd(event):
    await event.delete()
    ti = event.pattern_match.group(1).strip()
    tid, tname, err = await get_target(event, ti)
    if err:
        await client.send_message('me', err); return
    if tid:
        data["target_users"].add(tid)
        save_data()
        await client.send_message('me', f"🎯 تم إضافة {tname}")

# ------------------ الردود التلقائية ------------------
@client.on(events.NewMessage)
async def auto_reply(event):
    if not data["is_running"] or event.out or not data["lines"]:
        return
    sid = event.sender_id
    if sid in muted_private and event.is_private:
        try: await event.delete()
        except: pass
        return
    if sid in muted_group and event.is_group:
        try: await event.delete()
        except: pass
        return
    if sid in data["target_users"]:
        if sid not in data["locks"]:
            data["locks"][sid] = asyncio.Lock()
        if data["locks"][sid].locked():
            return
        async with data["locks"][sid]:
            text = get_distinct_lines(lines_per_message)
            await event.reply(text)

# ------------------ الأوامر ------------------
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.الاوامر$'))
async def help_cmd(event):
    await event.delete()
    help_text = f"""**{XLR_RIGHTS}**

**📋 الأوامر:**

**🎯 التفجير:**
`.توف [يوزر/ايدي]` - تفجير (ردود)
`.همم [يوزر/ايدي]` - تفجير بدون رد
`.تف [يوزر/ايدي]` - **رد تلقائي على رسائل الخاص**
`.تفو [يوزر/ايدي]` - **منشن مستمر في قروب**

**💥 السبام المخصص:**
`.سبام [عدد] [كلمة]` - يرسل الكلمة بعدد محدد
مثال: `.سبام 50 كس امك`

**📚 قاعدة السطور:**
`.قاعده` - عرض كل السطور
`.قاعده [تصنيف]` - عرض تصنيف معين
`.تصنيفات` - قائمة التصنيفات
`.تصنيف [اسم]` - تبديل تصنيف
`.رد` - إضافة سطور (بالرد)
`.مسح السطور` - مسح تصنيف

**🔇 الكتم:**
`.كتم خاص` / `.الغاء كتم خاص`
`.كتم قروب` / `.الغاء كتم قروب`

**⚙️ عام:**
`.تشغيل` / `.توقف`
`.وقت [رقم]` - التأخير
`.سريع` / `.بطيء`
`.عدد السطور [رقم]`
`.` - **إيقاف/استئناف مؤقت (Toggle)**
`.ايقاف الكل` - إيقاف المهام النشطة
`.تصفير`

**الحالة:** {'🟢' if data['is_running'] else '🔴'} | **التأخير:** {data['delay']}ث | **الأسطر:** {lines_per_message}
**التصنيف:** {current_category}"""
    await client.send_message('me', help_text)

# --------(---------- بدء التشغيل ------------------
async def main():
    await client.start()
    print("=" * 60)
    print("✅ سكربت XLR المعدل")
    print("📋 .الاوامر")
    print("🔥 .تفو @user - منشن مستمر")
    print("💬 .تف @user - رد على رسائل الخاص")
    print("💥 .سبام [عدد] [كلمة] - سبام مخصص")
    print("📚 .قاعده - عرض السطور")
    print("=" * 60)
    await client.run_until_disconnected()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())