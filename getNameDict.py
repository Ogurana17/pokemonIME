import requests, os, jaconv, re
from bs4 import BeautifulSoup

# 数字を漢数字に変換するマッピング
kanji_digits = ['', 'いち', 'に', 'さん', 'よん', 'ご', 'ろく', 'なな', 'はち', 'きゅう']
kanji_units = ['', 'じゅう', 'ひゃく', 'せん']
large_units = ['', 'まん', 'おく']

# アルファベットをひらがなに変換するマッピング
alphabet_hiragana = {
    'A': 'えー', 'B': 'びー', 'C': 'しー', 'D': 'でぃー', 'E': 'いー', 'F': 'えふ',
    'G': 'じー', 'H': 'えいち', 'I': 'あい', 'J': 'じぇい', 'K': 'けー', 'L': 'える',
    'M': 'えむ', 'N': 'えぬ', 'O': 'おー', 'P': 'ぴー', 'Q': 'きゅー', 'R': 'あーる',
    'S': 'えす', 'T': 'てぃー', 'U': 'ゆー', 'V': 'ぶい', 'W': 'だぶりゅー', 'X': 'えっくす',
    'Y': 'わい', 'Z': 'ぜっと'
}

# 数字を日本語の読み方に変換する関数
def convert_number_to_japanese(num):
    num_str = str(num)
    length = len(num_str)
    result = []

    for i, digit in enumerate(num_str):
        digit = int(digit)
        unit_position = (length - i - 1) % 4
        large_unit_position = (length - i - 1) // 4

        if digit == 0:
            continue  # 0はその桁でスキップ

        if digit > 1 or unit_position == 0:  # 「いちじゅう」「いちひゃく」とならないように
            result.append(kanji_digits[digit])

        result.append(kanji_units[unit_position])

        if unit_position == 0:  # まん、億などの大きい単位を付加
            result.append(large_units[large_unit_position])

    return ''.join(result)

# カタカナと数字をひらがなに変換する関数
def katakana_to_hiragana(text):
    # 数字のパターンを検出し、対応する日本語に変換
    text = re.sub(r'\d+', lambda x: convert_number_to_japanese(int(x.group())), text)
    # アルファベットをひらがなに変換
    text = ''.join([alphabet_hiragana.get(char.upper(), char) for char in text])
    # カタカナをひらがなに変換
    return jaconv.kata2hira(text)

# 辞書データを書き出す共通関数（TXT/Plist両対応）
# file_typeに応じてテキストまたはPlist形式で辞書を書き出す
def write_dictionary_to_file(file_type, dict_data, dir_path, file_path):
    os.makedirs(dir_path, exist_ok=True)
    if file_type == 'txt':
        # TXTファイルとして辞書を書き出し
        with open(file_path, 'w', encoding='utf-8') as f:
            for hiragana, original in dict_data.items():
                f.write(f'{hiragana}\t{original}\t固有名詞\t\n')
    elif file_type == 'plist':
        # Plistファイルのヘッダーとフッター
        header = '''<?xml version='1.0' encoding='UTF-8'?>\n<!DOCTYPE plist PUBLIC '-//Apple//DTD PLIST 1.0//EN' 'http://www.apple.com/DTDs/PropertyList-1.0.dtd'>\n<plist version='1.0'>\n<array>\n'''
        footer = '</array>\n</plist>\n'
        # Plistのデータフォーマット
        main_format = '\t<dict>\n\t\t<key>phrase</key>\n\t\t<string>{}</string>\n\t\t<key>shortcut</key>\n\t\t<string>{}</string>\n\t</dict>\n'

        # Plistファイルとして辞書を書き出し
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(header)
            for hiragana, original in dict_data.items():
                f.write(main_format.format(original, hiragana))
            f.write(footer)

# 外国語名のリストから辞書を生成する関数
# それぞれの辞書を作成して返す
def generate_dictionaries(foreign_names_list):
    number_to_kana_dict = {}  # 図鑑番号とカタカナ名の対応辞書
    number_to_eng_dict = {}   # 図鑑番号と英語名の対応辞書
    katakana_to_hiragana_dict = {}  # ひらがなとカタカナの対応辞書
    English_to_hiragana_dict = {}   # ひらがなと英語名の対応辞書

    for number, name, english_name in foreign_names_list:
        hiragana = katakana_to_hiragana(name)  # カタカナ名をひらがなに変換

        # 各辞書にデータを登録
        number_to_kana_dict[number] = name  # 図鑑番号とカタカナの対応
        number_to_eng_dict[number] = english_name   # 図鑑番号と英語名の対応
        katakana_to_hiragana_dict[hiragana] = name  # ひらがなとカタカナの対応
        English_to_hiragana_dict[hiragana] = english_name  # ひらがなと英語名の対応

    return number_to_kana_dict, number_to_eng_dict, katakana_to_hiragana_dict, English_to_hiragana_dict

# スクレイピングしてポケモンの外国語名一覧を取得する関数
def scrape_foreign_names(url, class_name):
    response = requests.get(url)  # URLからデータを取得
    soup = BeautifulSoup(response.content, 'html.parser')  # BeautifulSoupでHTML解析

    foreign_names_list = []
    tables = soup.find_all('table', {'class': class_name})  # 指定されたクラス名のテーブルを取得

    for table in tables:
        rows = table.find_all('tr')[1:]  # テーブルの各行（ヘッダー行をスキップ）
        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 3:
                number = cols[0].text.strip().lstrip('0') + 'p'   # 図鑑番号。先頭の0を削除して末尾に'p'を追加
                japanese_name = cols[1].text.strip()  # カタカナの名前
                english_name = cols[2].text.strip().split('(英語)')[0].strip()  # 英語の名前
                foreign_names_list.append((number, japanese_name, english_name))  # リストに追加

    return foreign_names_list

# データ元のURLとクラス名
url = 'https://wiki.xn--rckteqa2e.com/wiki/%E3%83%9D%E3%82%B1%E3%83%A2%E3%83%B3%E3%81%AE%E5%A4%96%E5%9B%BD%E8%AA%9E%E5%90%8D%E4%B8%80%E8%A6%A7'
class_name = 'graytable'

# 外国語名のリストをスクレイピングして取得
foreign_names_list = scrape_foreign_names(url, class_name)

# 辞書を生成
number_to_kana_dict, number_to_eng_dict, katakana_to_hiragana_dict, English_to_hiragana_dict = generate_dictionaries(foreign_names_list)

# 辞書をファイルに書き出し（TXT形式とPlist形式）
file_name = 'Name'

write_dictionary_to_file('txt', number_to_kana_dict, file_name, file_name + '/pokemon' + file_name + 'IMEDictNum2Kata.txt')
write_dictionary_to_file('txt', number_to_eng_dict, file_name, file_name + '/pokemon' + file_name + 'IMEDictNum2Eng.txt')
write_dictionary_to_file('txt', katakana_to_hiragana_dict, file_name, file_name + '/pokemon' + file_name + 'IMEDictHira2Kata.txt')
write_dictionary_to_file('txt', English_to_hiragana_dict, file_name, file_name + '/pokemon' + file_name + 'IMEDictHira2Eng.txt')
write_dictionary_to_file('plist', number_to_kana_dict, file_name, file_name + '/pokemon' + file_name + 'IMEDictNum2Kata.plist')
write_dictionary_to_file('plist', number_to_eng_dict, file_name, file_name + '/pokemon' + file_name + 'IMEDictNum2Eng.plist')
write_dictionary_to_file('plist', katakana_to_hiragana_dict, file_name, file_name + '/pokemon' + file_name + 'IMEDictHira2Kata.plist')
write_dictionary_to_file('plist', English_to_hiragana_dict, file_name, file_name + '/pokemon' + file_name + 'IMEDictHira2Eng.plist')

print('辞書ファイルの作成が完了しました。')
