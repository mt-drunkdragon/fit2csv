import csv
import os
import sys
import zipfile
import tempfile
from fitparse import FitFile

# 2026/6/23 のFITデータ解析で、TCXとの比較から推定したラベル対応表。
# 同一デバイス・同一ファームウェアであれば基本的に同じ意味になるはずです。
# 確信度が低いものはコメントで明記しています。
LABEL_MAP = {
    'unknown_136': 'heart_rate_raw',      # heart_rate列と完全一致(重複フィールド)
    'unknown_140': 'power_raw_dw',        # power列のおよそ10倍 → 未スケールの生値(0.1W単位)と推定
    'unknown_135': 'gps_accuracy',        # 起動直後は大きく、GPSロック後に小さい値で安定 → 推定位置誤差(EPE)
    'unknown_143': 'battery_soc',         # 53〜70の範囲でランの経過に伴い緩やかに減少 → バッテリー残量(%)
    'unknown_107': 'gps_fix',             # 開始直後0→以降1で安定 → GPSフィックス取得フラグ
    # 以下は確信度が低いため、ラベル名はそのまま保持(末尾に _unconfirmed を付与)
    'unknown_90': 'unknown_90_unconfirmed',
    'unknown_87': 'unknown_87_unconfirmed',
    'unknown_134': 'unknown_134_unconfirmed',
}


def fit_to_csv(fit_file_path, output_csv_path):
    # FITファイルの読み込み
    fitfile = FitFile(fit_file_path)

    # 記録されたデータを全て取得
    records = []
    for message in fitfile.get_messages('record'):
        record_data = {}
        for record in message:
            record_data[record.name] = record.value
        records.append(record_data)

    if not records:
        print("レコードデータが見つかりませんでした。")
        return

    # 全ての一意なキー（カラム名）を取得
    fieldnames = set()
    for record in records:
        fieldnames.update(record.keys())

    # ラベル対応表でリネーム（対応表に無い列名はそのまま）
    renamed_fieldnames = [LABEL_MAP.get(name, name) for name in fieldnames]

    # CSVへの書き出し（列名をリネームしつつ出力）
    with open(output_csv_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=renamed_fieldnames)
        writer.writeheader()
        for record in records:
            renamed_row = {LABEL_MAP.get(k, k): v for k, v in record.items()}
            writer.writerow(renamed_row)

    print(f"変換が完了しました: {output_csv_path}")


def extract_fit_from_zip(zip_path, extract_dir):
    """ZIP内から最初に見つかった.fitファイルを展開してパスを返す"""
    with zipfile.ZipFile(zip_path, 'r') as z:
        fit_names = [n for n in z.namelist() if n.lower().endswith('.fit')]
        if not fit_names:
            raise ValueError("ZIP内に.fitファイルが見つかりませんでした。")
        # 複数ある場合は最初の1つを使用
        fit_name = fit_names[0]
        z.extract(fit_name, extract_dir)
        return os.path.join(extract_dir, fit_name)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("使い方: python fit2csv.py <入力.fit または 入力.zip>")
        sys.exit(1)

    input_path = sys.argv[1]
    base, ext = os.path.splitext(input_path)

    if ext.lower() == '.zip':
        with tempfile.TemporaryDirectory() as tmp_dir:
            fit_file = extract_fit_from_zip(input_path, tmp_dir)
            csv_file = base + '.csv'  # 出力名はZIPファイル名ベース
            fit_to_csv(fit_file, csv_file)
    elif ext.lower() == '.fit':
        fit_file = input_path
        csv_file = base + '.csv'
        fit_to_csv(fit_file, csv_file)
    else:
        print("対応していない拡張子です。.fitまたは.zipを指定してください。")
        sys.exit(1)