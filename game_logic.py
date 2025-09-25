import json

ARTIFACT_NAMES = [
    "Шлих 〽️", "Талисман удачи 🧿", "Рюкзак бездны 🎒", "Кинжал убийцы 🔪",
    "Магический верстак 🗜️", "Волшебный шар 🔮", "Ученая степень 🔎", "Компас 🧭"
]

def get_artifact_levels(levels_str):
    try:
        return json.loads(levels_str)
    except:
        return [0] * 8

def set_artifact_levels(levels_list):
    return json.dumps(levels_list)

def get_artifact_info(artifact_id, level):
    info = {
        0: f"Шлих 〽️\nУровень: {level}\nВместимость монет: {1000 * (1.25 ** level):,.0f}\nДоход: {0.25 * (level // 10):.2f} 🪙/сек",
        1: f"Талисман удачи 🧿\nУровень: {level}\nШанс мешочка золота: {0.1 * (level // 5):.1f}%\nШанс коробки: {0.01 * (level // 10):.2f}%\nШанс билета: {0.005 * (level // 25):.3f}%",
        2: f"Рюкзак бездны 🎒\nУровень: {level}\nВместимость ресурсов: {5000 * (1.3 ** level):,.0f}",
        3: f"Кинжал убийцы 🔪\nУровень: {level}\n+{2 * level} очков\n+{20 * (level // 10)} очков\n+{5 * (level // 10)} мин к приключению",
        4: f"Магический верстак 🗜️\nУровень: {level}\nДобыча: {5 * level} 🔫/мин\nВместимость: {100 + 10 * level} 🔫",
        5: f"Волшебный шар 🔮\nУровень: {level}\nДобыча пыли: {2 * level + 20 * (level // 10)} ✨/сек\nШанс 💷: {0.05 * (level // 10):.2f}%",
        6: f"Ученая степень 🔎\nУровень: {level}\nМакс. навыков в обсерватории: {1 + (level // 10)}",
        7: f"Компас 🧭\nУровень: {level}\nДобыча частей: {2 * level + 20 * (level // 10)} ⚱️/мин\nШанс 💰 в данже: {0.08 * (level // 10):.2f}%"
    }
    return info.get(artifact_id, "Неизвестный артефакт")

def get_upgrade_cost(level):
    # Пример: экспоненциальный рост
    return {
        'coins': int(100 * (1.5 ** level)),
        'artifact_parts': int(10 * (1.4 ** level)),
        'magic_dust': int(5 * (1.3 ** level))
    }
