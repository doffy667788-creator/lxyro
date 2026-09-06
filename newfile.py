import asyncio
import json
import os
import random
import time
from datetime import datetime
from telethon import TelegramClient, events, errors
from telethon.tl.types import Channel, Chat, User
from telethon.tl.functions.account import UpdateProfileRequest
from telethon.tl.functions.contacts import BlockRequest, UnblockRequest

# ------------------ إعدادات الحساب ------------------
API_ID =37339814 
API_HASH = 'ae48a0532f231876e98751b21263ae26'

client = TelegramClient('session_name', API_ID, API_HASH)

DATA_FILE = "script_data.json"
INSULTS_DB_FILE = "insults_db.json"
NAMES_FILE = "scheduled_names.json"

XLR_RIGHTS = "𝗫𝗟𝗥 𝗦𝗼𝘂𝗿𝗰𝗲 | @rlor1"

active_bombings = {}
muted_users = set()
paused = False
current_category = "مفرداتي"
targets_info = {}

# ------------------ إدارة الأسماء المجدولة ------------------
def load_scheduled_names():
    if os.path.exists(NAMES_FILE):
        with open(NAMES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_scheduled_names(names):
    with open(NAMES_FILE, 'w', encoding='utf-8') as f:
        json.dump(names, f, ensure_ascii=False, indent=4)

scheduled_names = load_scheduled_names()

async def name_changer_task():
    """مهمة خلفية لتغيير الاسم حسب الجدول"""
    while True:
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        for entry in scheduled_names:
            if entry.get("time") == current_time:
                new_name = entry["name"]
                try:
                    await client(UpdateProfileRequest(first_name=new_name))
                    print(f"✅ تم تغيير الاسم إلى {new_name} في {current_time}")
                    await client.send_message('me', f"🔄 تم تغيير الاسم إلى: {new_name}")
                except Exception as e:
                    print(f"❌ فشل تغيير الاسم: {e}")
        await asyncio.sleep(60)

# ------------------ قاعدة بيانات السب ------------------
def load_insults_db():
    if os.path.exists(INSULTS_DB_FILE):
        with open(INSULTS_DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        default_lines = [
            "ابن سيكوباثيه", "ابن المجرمه", "ابن الزنجيه", "ابن العنتيله",
            "ابن الدبه القحبه", "ابن الكلبه الامريكيه", "ابن المنيوكه السافله",
            "ابن القحبانيه", "ابن الاغريقيه", "ابن السافله", "ابن الكافره",
            "ابن الزنديق", "ابن البوذيه", "ابن الوحشيه", "ابن الكلبانيه",
            "يخو المنيوكييه", "يبن المطروحه", "انيك والدينك يبن حماره",
            "انيك قبيلتك ي ديوث", "انيك ميجار اهلك", "انيك ميجار امك",
            "انيك امك القحبه", "انيك اختك الزانيه", "انيك امك الواشيه",
            "انكح امك الخياطه", "انيك امك هيه زعلانه", "انيك امك ب غرفت ابوك",
            "يابن المتلطمه", "يابن ليبراليه", "يابن المحروقه", "يابن المنكوحه",
            "كس امك بجزمتي", "يابن الايرانديه", "يابن الخليجيه", "يابن البابليه",
            "يابن الفرعونيه", "يابن الجزمه", "يابن النعال", "يابن القندرا",
            "يابن الديموراطيه", "يابن المليوصه", "يابن البربوصه", "يابن المعموصه",
            "يابن المتفشله", "يابن المستعبده", "يابن الجلوخيه", "يابن السكساويه",
            "يابن الممزوغ", "يابن الغوله", "يابن الشنوطيه", "يابن المطقوق",
            "يابن المكسورا", "يابن الفاسقه", "يابن الحبشيه", "يابن الفارسيه",
            "يابن الامازيغيه", "يابن الغجريه", "يابن الشوعيه", "يابن النازيه",
            "يابن السوفيتيه", "يابن المتفجره", "يخو المنفلقه", "يخو المفقحه",
            "يخو المبقعه"
        ]
        default_lines = list(set(default_lines))
        default_db = {"مفرداتي": default_lines}
        with open(INSULTS_DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(default_db, f, ensure_ascii=False, indent=4)
        return default_db

insults_db = load_insults_db()

# ------------------ دالة لاختيار عدد عشوائي من السطور ودمجها (بدون تنويع) ------------------
def get_multiple_lines_combined(min_lines=4, max_lines=6):
    """تجميع عدد عشوائي من السطور (بين min_lines و max_lines) في سطر واحد"""
    lines = data["lines"]
    if len(lines) == 0:
        return ""
    count = random.randint(min_lines, max_lines)
    selected = random.choices(lines, k=count)
    combined = " ".join(selected)
    return combined

# ------------------ بيانات التحكم الأساسية ------------------
data = {
    "is_running": True,
    "allow_private": True,
    "delay": 2,
    "target_users": set(),
    "lines": insults_db.get(current_category, []),
    "current_index": 0,
    "locks": {}
}

def save_data():
    serializable_targets = list(data["target_users"])
    save_dict = {
        "is_running": data["is_running"],
        "allow_private": data["allow_private"],
        "delay": data["delay"],
        "target_users": serializable_targets,
        "current_index": data["current_index"],
        "current_category": current_category
    }
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(save_dict, f, ensure_ascii=False, indent=4)

def load_data():
    default_data = {
        "is_running": True,
        "allow_private": True,
        "delay": 2,
        "target_users": [],
        "current_index": 0,
        "current_category": "مفرداتي"
    }
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

# ------------------ دالة مساعدة للحصول على الهدف ------------------
async def get_target_from_event(event, input_text):
    target = None
    target_id = None
    target_name = ""

    if event.is_reply and not input_text:
        reply = await event.get_reply_message()
        target = await reply.get_sender()
        target_id = target.id
        target_name = f"@{target.username}" if target.username else str(target_id)
    elif input_text:
        try:
            text = input_text.strip()
            if text.isdigit() or (text.startswith('-') and text[1:].isdigit()):
                target_id = int(text)
                target_name = str(target_id)
            else:
                target = await client.get_entity(text)
                target_id = target.id
                target_name = f"@{target.username}" if target.username else str(target_id)
        except ValueError:
            return None, None, "❌ الإدخال غير صالح."
        except Exception as e:
            return None, None, f"❌ خطأ في العثور على المستخدم: {e}"
    else:
        return None, None, "⚠️ حدد الهدف."

    return target_id, target_name, None

# ------------------ مهمة التفجير (إرسال عادي) ------------------
async def bombing_task(target_id, target_name, chat_id, reply_to_msg_id, is_private, mention=False):
    global paused
    total = len(data["lines"])
    if total == 0:
        return

    target_messages = []
    if not is_private and reply_to_msg_id:
        try:
            msgs = await client.get_messages(chat_id, limit=10, from_user=target_id)
            target_messages = [msg.id for msg in msgs if msg]
            if not target_messages:
                target_messages = [reply_to_msg_id]
        except:
            target_messages = [reply_to_msg_id] if reply_to_msg_id else []
    msg_update_counter = 0

    while target_id in active_bombings and data["is_running"]:
        if paused:
            await asyncio.sleep(1)
            continue

        combined = get_multiple_lines_combined()

        if mention and not is_private:
            combined = f"@{target_name} {combined}"

        if is_private:
            async with client.action(chat_id, 'typing'):
                await asyncio.sleep(data["delay"])
            await client.send_message(chat_id, combined)
        else:
            current_reply = random.choice(target_messages) if target_messages else reply_to_msg_id
            msg_update_counter += 1
            if msg_update_counter >= 5:
                try:
                    msgs = await client.get_messages(chat_id, limit=10, from_user=target_id)
                    new_ids = [msg.id for msg in msgs if msg]
                    if new_ids:
                        target_messages = new_ids
                    msg_update_counter = 0
                except:
                    pass
            async with client.action(chat_id, 'typing'):
                await asyncio.sleep(data["delay"])
            await client.send_message(chat_id, combined, reply_to=current_reply)

        await asyncio.sleep(0.3)

    if target_id in active_bombings:
        del active_bombings[target_id]

# ------------------ مهمة السبام ------------------
async def spam_task(target_id, target_name, chat_id, reply_to_msg_id, is_private, count, mention=False):
    """إرسال عدد محدد من الرسائل (توقف بعد الانتهاء)"""
    if not data["lines"]:
        return

    target_messages = []
    if not is_private and reply_to_msg_id:
        try:
            msgs = await client.get_messages(chat_id, limit=10, from_user=target_id)
            target_messages = [msg.id for msg in msgs if msg]
            if not target_messages:
                target_messages = [reply_to_msg_id]
        except:
            target_messages = [reply_to_msg_id] if reply_to_msg_id else []
    msg_update_counter = 0

    for _ in range(count):
        if not data["is_running"] or target_id not in active_bombings:
            break
        if paused:
            await asyncio.sleep(1)
            continue

        combined = get_multiple_lines_combined()

        if mention and not is_private:
            combined = f"@{target_name} {combined}"

        if is_private:
            async with client.action(chat_id, 'typing'):
                await asyncio.sleep(data["delay"])
            await client.send_message(chat_id, combined)
        else:
            current_reply = random.choice(target_messages) if target_messages else reply_to_msg_id
            msg_update_counter += 1
            if msg_update_counter >= 5:
                try:
                    msgs = await client.get_messages(chat_id, limit=10, from_user=target_id)
                    new_ids = [msg.id for msg in msgs if msg]
                    if new_ids:
                        target_messages = new_ids
                    msg_update_counter = 0
                except:
                    pass
            async with client.action(chat_id, 'typing'):
                await asyncio.sleep(data["delay"])
            await client.send_message(chat_id, combined, reply_to=current_reply)

        await asyncio.sleep(0.3)

    if target_id in active_bombings:
        del active_bombings[target_id]

# ------------------ دالة بدء التفجير ------------------
async def start_bombing(event, cmd_type):
    global paused
    if not data["is_running"]:
        return await event.edit("⚠️ السكربت متوقف")
    if paused:
        return await event.edit("⚠️ الأوامر موقوفة مؤقتاً")
    if not data["lines"]:
        return await event.edit("⚠️ لا توجد سطور في قاعدة البيانات")

    input_text = event.pattern_match.group(1) if event.pattern_match else None
    target_id, target_name, err = await get_target_from_event(event, input_text)
    if err:
        return await event.edit(err)

    if target_name.isdigit() and not target_name.startswith('@'):
        try:
            entity = await client.get_entity(target_id)
            target_name = f"@{entity.username}" if entity.username else str(entity.id)
        except:
            target_name = str(target_id)

    if target_id in active_bombings:
        return await event.edit(f"⚠️ الهدف {target_name} قيد التفجير بالفعل")

    is_private = False
    reply_needed = False
    no_reply = False
    mention = False
    is_spam = False
    spam_count = 0

    if cmd_type == 'private':
        is_private = True
    elif cmd_type == 'group':
        is_private = False
        reply_needed = True
    elif cmd_type == 'group_mention':
        is_private = False
        reply_needed = True
        mention = True
    elif cmd_type == 'group_noreply':
        is_private = False
        reply_needed = False
    elif cmd_type.startswith('spam'):
        parts = cmd_type.split()
        if len(parts) == 2:
            try:
                spam_count = int(parts[1])
            except:
                return await event.edit("⚠️ عدد غير صحيح.")
        else:
            spam_count = 10
        is_spam = True
        if event.is_private:
            is_private = True
            reply_needed = False
        else:
            is_private = False
            reply_needed = True
            mention = False

    found_msg_id = None
    chat_id = None

    if not is_private:
        if reply_needed:
            async for dialog in client.iter_dialogs(limit=25):
                if dialog.is_group:
                    async for msg in client.iter_messages(dialog.id, limit=30, from_user=target_id):
                        found_msg_id = msg.id
                        chat_id = dialog.id
                        break
                if found_msg_id:
                    break
            if not found_msg_id:
                return await event.edit(f"❌ لا توجد رسائل للهدف {target_name} في القروبات")
        elif no_reply:
            async for dialog in client.iter_dialogs(limit=25):
                if dialog.is_group:
                    chat_id = dialog.id
                    break
            if not chat_id:
                return await event.edit(f"❌ لم يتم العثور على قروب مشترك")
    else:
        chat_id = target_id

    targets_info[target_id] = {
        "target_name": target_name,
        "chat_id": chat_id,
        "reply_to_msg_id": found_msg_id if reply_needed else None,
        "is_private": is_private,
        "mention": mention,
        "spam": is_spam,
        "spam_count": spam_count if is_spam else 0
    }

    if is_spam:
        task = asyncio.create_task(spam_task(target_id, target_name, chat_id,
                                             found_msg_id if reply_needed else None,
                                             is_private, spam_count, mention))
    else:
        task = asyncio.create_task(bombing_task(target_id, target_name, chat_id,
                                                found_msg_id if reply_needed else None,
                                                is_private, mention))
    active_bombings[target_id] = task

    msg_type = "سبام" if is_spam else "تفجير"
    await event.edit(f"✅ بدأ {msg_type} على {target_name}")

# ------------------ أوامر التفجير والسبام ------------------
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.توف(?:\s+(.+))?$'))
async def bomb_in_group(event):
    await start_bombing(event, 'group')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.همم(?:\s+(.+))?$'))
async def bomb_noreply(event):
    await start_bombing(event, 'group_noreply')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.تف(?:\s+(.+))?$'))
async def bomb_private(event):
    await start_bombing(event, 'private')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.تفو(?:\s+(.+))?$'))
async def bomb_mention(event):
    await start_bombing(event, 'group_mention')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.سبام(?:\s+(\S+)(?:\s+(\d+))?)?$'))
async def spam_command(event):
    match = event.pattern_match
    if match and match.group(1):
        target = match.group(1)
        count = match.group(2) if match.group(2) else "10"
        cmd = f"spam {count}"
        # نقوم بإنشاء كائن مؤقت لنقل الهدف
        event.pattern_match = type('obj', (object,), {'group': lambda x: target})()
        await start_bombing(event, cmd)
    else:
        await event.edit("⚠️ استخدم: `.سبام @user 5`")

# ------------------ أوامر السرعة ------------------
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.سريع$'))
async def set_fast(event):
    data["delay"] = 0.2
    save_data()
    await event.edit("⚡ تم ضبط السرعة الفائقة (0.2 ثانية)")

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.بطيء$'))
async def set_slow(event):
    data["delay"] = 2
    save_data()
    await event.edit("🐢 تم ضبط السرعة العادية (2 ثانية)")

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.تأخير (\d+(?:\.\d+)?)$'))
async def set_custom_delay(event):
    val = float(event.pattern_match.group(1))
    if val < 0.1:
        await event.edit("⚠️ التأخير صغير جداً.")
        return
    data["delay"] = val
    save_data()
    await event.edit(f"⏱️ تم ضبط التأخير إلى {val} ثانية")

# ------------------ ميزة النقطة ------------------
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.$'))
async def toggle_pause(event):
    global paused
    paused = not paused
    status = "موقوفة" if paused else "مستأنفة"
    await client.send_message('me', f"⚡ الأوامر الآن {status}.")

    if paused:
        for tid, task in list(active_bombings.items()):
            task.cancel()
        active_bombings.clear()
        await client.send_message('me', f"🛑 تم إيقاف {len(targets_info)} مهمة.")
    else:
        restarted = 0
        for tid, info in list(targets_info.items()):
            if tid not in active_bombings:
                if info.get("spam"):
                    task = asyncio.create_task(spam_task(tid, info["target_name"],
                                                          info["chat_id"],
                                                          info["reply_to_msg_id"],
                                                          info["is_private"],
                                                          info.get("spam_count", 10),
                                                          info.get("mention", False)))
                else:
                    task = asyncio.create_task(bombing_task(tid, info["target_name"],
                                                             info["chat_id"],
                                                             info["reply_to_msg_id"],
                                                             info["is_private"],
                                                             info.get("mention", False)))
                active_bombings[tid] = task
                restarted += 1
        await client.send_message('me', f"✅ تم استئناف {restarted} مهمة.")

# ------------------ أوامر إدارة قاعدة البيانات ------------------
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.تصنيفات$'))
async def list_categories(event):
    cats = list(insults_db.keys())
    msg = "**📂 التصنيفات المتاحة:**\n\n"
    for i, cat in enumerate(cats, 1):
        msg += f"{i}. {cat} ({len(insults_db[cat])} سطر)\n"
    msg += f"\n**الحالي:** {current_category}"
    await event.edit(msg)

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.تصنيف (.+)$'))
async def change_category(event):
    global current_category
    cat = event.pattern_match.group(1).strip()
    if cat in insults_db:
        current_category = cat
        data["lines"] = insults_db[cat]
        data["current_index"] = 0
        save_data()
        await event.edit(f"✅ تم التبديل إلى **{cat}** ({len(data['lines'])} سطر).")
    else:
        await event.edit("❌ هذا التصنيف غير موجود.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.رد$'))
async def add_lines(event):
    if event.is_reply:
        reply = await event.get_reply_message()
        new_lines = [l.strip() for l in reply.text.split('\n') if l.strip()]
        insults_db[current_category].extend(new_lines)
        data["lines"] = insults_db[current_category]
        with open(INSULTS_DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(insults_db, f, ensure_ascii=False, indent=4)
        save_data()
        await event.edit(f"✅ تم حفظ {len(new_lines)} سطر. الإجمالي: {len(data['lines'])}")
    else:
        await event.edit("⚠️ رد على النص.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.مسح السطور$'))
async def clear_lines(event):
    insults_db[current_category] = []
    data["lines"] = []
    data["current_index"] = 0
    with open(INSULTS_DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(insults_db, f, ensure_ascii=False, indent=4)
    save_data()
    await event.edit(f"🗑 تم مسح سطور '{current_category}'.")

# ------------------ أوامر الكتم والطرد ------------------
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.كتم(?:\s+(.+))?$'))
async def mute_user(event):
    input_text = event.pattern_match.group(1)
    if not input_text and not event.is_reply:
        return await event.edit("⚠️ استخدم `.كتم @يوزر` أو بالرد")
    target = None
    if event.is_reply and not input_text:
        reply = await event.get_reply_message()
        target = reply.sender_id
    else:
        try:
            text = input_text.strip()
            if text.isdigit() or (text.startswith('-') and text[1:].isdigit()):
                target = int(text)
            else:
                entity = await client.get_entity(text)
                target = entity.id
        except:
            return await event.edit("❌ لم يتم العثور على المستخدم")
    muted_users.add(target)
    await event.edit(f"🔇 تم كتم `{target}`.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.الغاء الكتم(?:\s+(.+))?$'))
async def unmute_user(event):
    input_text = event.pattern_match.group(1)
    if not input_text and not event.is_reply:
        return await event.edit("⚠️ استخدم `.الغاء الكتم @يوزر` أو بالرد")
    target = None
    if event.is_reply and not input_text:
        reply = await event.get_reply_message()
        target = reply.sender_id
    else:
        try:
            text = input_text.strip()
            if text.isdigit() or (text.startswith('-') and text[1:].isdigit()):
                target = int(text)
            else:
                entity = await client.get_entity(text)
                target = entity.id
        except:
            return await event.edit("❌ لم يتم العثور على المستخدم")
    muted_users.discard(target)
    await event.edit(f"🔊 تم إلغاء كتم `{target}`.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.قائمة الكتم$'))
async def list_muted(event):
    if not muted_users:
        await event.edit("📭 قائمة الكتم فارغة.")
        return
    msg = "**🔇 قائمة المكتمومين:**\n\n"
    for uid in muted_users:
        try:
            entity = await client.get_entity(uid)
            name = f"@{entity.username}" if entity.username else f"{entity.first_name or ''} {entity.last_name or ''}".strip()
            msg += f"• {name} (`{uid}`)\n"
        except:
            msg += f"• `{uid}`\n"
    await event.edit(msg)

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.طرد(?:\s+(.+))?$'))
async def target_user(event):
    input_text = event.pattern_match.group(1)
    target_id, target_name, err = await get_target_from_event(event, input_text)
    if err:
        return await event.edit(err)
    if target_id:
        data["target_users"].add(target_id)
        save_data()
        await event.edit(f"🎯 تم إضافة `{target_name}` للاستهداف.")

# ------------------ أوامر إدارة الأسماء المجدولة ------------------
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.اضافة اسم (.+?) (\d{1,2}):(\d{2})$'))
async def add_scheduled_name(event):
    name = event.pattern_match.group(1).strip()
    hour = int(event.pattern_match.group(2))
    minute = int(event.pattern_match.group(3))
    time_str = f"{hour:02d}:{minute:02d}"
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        await event.edit("⚠️ وقت غير صالح (ساعة 0-23، دقيقة 0-59).")
        return
    scheduled_names.append({"name": name, "time": time_str})
    save_scheduled_names(scheduled_names)
    await event.edit(f"✅ تم إضافة الاسم '{name}' في الساعة {time_str}.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.حذف اسم (\d+)$'))
async def remove_scheduled_name(event):
    idx = int(event.pattern_match.group(1)) - 1
    if 0 <= idx < len(scheduled_names):
        removed = scheduled_names.pop(idx)
        save_scheduled_names(scheduled_names)
        await event.edit(f"🗑 تم حذف الاسم '{removed['name']}'.")
    else:
        await event.edit("❌ الرقم غير صحيح.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.قائمة الأسماء$'))
async def list_scheduled_names(event):
    if not scheduled_names:
        await event.edit("📭 لا توجد أسماء مجدولة.")
        return
    msg = "**📝 الأسماء المجدولة:**\n\n"
    for i, entry in enumerate(scheduled_names, 1):
        msg += f"{i}. {entry['name']} - الساعة {entry['time']}\n"
    await event.edit(msg)

# ------------------ أوامر أخرى ------------------
@client.on(events.NewMessage(pattern=r'^\.مسح رسائلي$', outgoing=True))
async def delete_all_my_messages(event):
    chat = await event.get_input_chat()
    await event.delete()
    messages_to_delete = []
    count = 0
    async for message in client.iter_messages(chat, from_user='me'):
        messages_to_delete.append(message.id)
        count += 1
        if len(messages_to_delete) == 100:
            await client.delete_messages(chat, messages_to_delete)
            messages_to_delete = []
            await asyncio.sleep(1)
    if messages_to_delete:
        await client.delete_messages(chat, messages_to_delete)
    await event.respond(f"✅ تم حذف {count} رسالة.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.تفعيل الخاص$'))
async def enable_pv(event):
    data["allow_private"] = True
    save_data()
    await event.edit("✅ تم تفعيل الخاص.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.تعطيل الخاص$'))
async def disable_pv(event):
    data["allow_private"] = False
    save_data()
    await event.edit("❌ تم تعطيل الخاص.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.توقف$'))
async def stop_script(event):
    global paused
    for info in list(active_bombings.values()):
        info.cancel()
    active_bombings.clear()
    targets_info.clear()
    data["is_running"] = False
    paused = False
    save_data()
    await event.edit("🛑 **تم إيقاف السكربت**")

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.تشغيل$'))
async def start_script(event):
    data["is_running"] = True
    save_data()
    await event.edit("▶️ **تم تشغيل السكربت**")

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.وقت (\d+)$'))
async def set_delay(event):
    data["delay"] = int(event.pattern_match.group(1))
    save_data()
    await event.edit(f"⏳ تم ضبط التأخير: {data['delay']} ثانية")

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.تصفير$'))
async def clear_all(event):
    for info in list(active_bombings.values()):
        info.cancel()
    active_bombings.clear()
    targets_info.clear()
    data["target_users"].clear()
    save_data()
    await event.edit("🛑 تم إيقاف الكل ومسح المستهدفين.")

# ------------------ الردود التلقائية ------------------
@client.on(events.NewMessage)
async def handle_replies(event):
    if not data["is_running"] or event.out or not data["lines"]:
        return
    sender_id = event.sender_id
    if sender_id in muted_users and event.is_private:
        try:
            await event.delete()
        except:
            pass
        return
    is_target = sender_id in data["target_users"]
    if (event.is_private and data["allow_private"]) or is_target:
        if sender_id not in data["locks"]:
            data["locks"][sender_id] = asyncio.Lock()
        if data["locks"][sender_id].locked():
            return
        async with data["locks"][sender_id]:
            async with client.action(event.chat_id, 'typing'):
                await asyncio.sleep(data["delay"])
            combined = get_multiple_lines_combined()
            await event.reply(combined)
            await asyncio.sleep(0.3)

# ------------------ أمر المساعدة ------------------
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.الاوامر$'))
async def show_commands(event):
    status = "🟢 نشط" if data["is_running"] else "🔴 متوقف"
    pause_status = "موقوفة" if paused else "مستأنفة"
    help_text = f"""**{XLR_RIGHTS}**

**❶ الخاص**
`.تف [يوزر/ايدي]` : تفجير خاص
`.كتم` / `.الغاء الكتم` : كتم/إلغاء كتم
`.قائمة الكتم` : عرض المكتمومين

**❷ القروبات**
`.توف [يوزر/ايدي]` : تفجير ردود
`.همم [يوزر/ايدي]` : بدون رد
`.تفو [يوزر/ايدي]` : تفجير مع منشن
`.سبام [يوزر/ايدي] [عدد]` : إرسال عدد محدد من الرسائل (افتراضي 10)

**❸ تغيير الاسم تلقائياً**
`.اضافة اسم [الاسم] [ساعة:دقيقة]` : إضافة اسم للتغيير في الوقت المحدد
`.حذف اسم [رقم]` : حذف اسم من القائمة
`.قائمة الأسماء` : عرض الأسماء المجدولة

**❹ السرعة**
`.سريع` (0.2 ث) / `.بطيء` (2 ث)
`.تأخير [رقم]` : تأخير مخصص

**❺ قاعدة البيانات**
`.تصنيفات` : عرض التصنيفات
`.تصنيف [اسم]` : التبديل
`.رد` : إضافة سطور (بالرد)
`.مسح السطور` : مسح التصنيف الحالي

**❻ أخرى**
`.طرد [يوزر/ايدي]` : استهداف للردود
`.تشغيل / .توقف` : تشغيل/إيقاف
`.وقت [رقم]` : ضبط التأخير (ثواني)
`.تصفير` : إيقاف الكل
`.مسح رسائلي` : حذف رسائلك

**حالة:** {status} | **إيقاف مؤقت:** {pause_status}
**التصنيف:** {current_category} ({len(data['lines'])} سطر)"""
    await event.edit(help_text)

# ------------------ بدء المهام الخلفية ------------------
async def background_tasks():
    await client.start()
    asyncio.create_task(name_changer_task())
    await client.run_until_disconnected()

# ------------------ شاشة البداية ------------------
print("=" * 60)
print("✅ سكربت السب المتكامل (بدون تنويع)")
print("📋 .الاوامر")
print("📂 تصنيفات: .تصنيفات / .تصنيف [اسم]")
print("🎯 تفجير: .توف / .تف / .همم / .تفو")
print("💥 سبام: .سبام @user 10")
print("🕒 تغيير الاسم: .اضافة اسم أحمد 14:30")
print("⚡ سرعة: .سريع / .بطيء / .تأخير")
print("=" * 60)
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(background_tasks())