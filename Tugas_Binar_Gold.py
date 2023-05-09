import re # Memanggil regex
import sqlite3 # Memanggil database
import pandas as pd # Memanggil data

from flask import Flask, jsonify, request # Memanggil flask
from flasgger import Swagger, LazyString, LazyJSONEncoder, swag_from ##Memanggil Swagger

# Untuk menjelaskan nama modul yang digunakan, sehingga ketika folder lain memanggil folder app akan otomatis teridentifikasi.
app = Flask(__name__)

# Untuk membaca api
app.json_encoder = LazyJSONEncoder

# Merubah tulisan template halaman host 
swagger_template = dict(
    info = {
        'title': LazyString(lambda: 'API Documentation BINAR CHALLENGE'),
        'version': LazyString(lambda: '1.0.0 // BETA'),
        'description': LazyString(lambda: 'API Documentation for Text Processing'),
    },
    host = LazyString(lambda: request.host)
)

# Konfigurasi alamat halaman akses, dll
swagger_config = {
    'headers': [],
    'specs': [
        {
            'endpoint': 'docs',
            'route': '/docs.json',
        }
    ],
    'static_url_path': '/flasgger_static',
    'swagger_ui': True,
    'specs_route':'/'
}

# Menggabungkan template dan konfigurasi dalam satu variabel
swagger = Swagger(app, template = swagger_template, config = swagger_config)

# Fungsi menjadikan tulisan kecil semua 
def lowercase(huruf):
    return huruf.lower()

def perbaiki_kalimat(huruf):
    # menghapus website
    huruf = re.sub('((www\.[^\s]+)|(https?://[^\s]+)|(http?://[^\s]+))',' ', huruf)

    # hapus link
    huruf = re.sub(r'https://t.co/\w+', ' ', huruf)

    # mengganti setiap karakter newline (baris baru) dalam string huruf dengan spasi (' ')
    huruf = re.sub('\n',' ',huruf)

    # mengganti setiap kemunculan substring "rt" dalam string huruf dengan spasi (' ')
    huruf = re.sub('rt',' ', huruf)

    # mengganti setiap kemunculan dua atau lebih spasi berturut-turut dalam string huruf dengan satu spasi (' ')
    huruf = re.sub('  +', ' ', huruf)
    
    # menghapus setiap kemunculan substring yang dimulai dengan "pic.twitter.com." 
    # diikuti oleh satu atau lebih karakter alfanumerik dalam string huruf, dan mengembalikan string baru yang sudah diproses
    huruf = re.sub(r'pic.twitter.com.[\w]+', '', huruf)

    # menghapus kata user
    huruf = re.sub('user',' ', huruf)

    # menghapus kata yang diawalki huruf x sebanyak yang memiliki 3 huruf, contoh: xf0
    huruf = re.sub(r"\bx\w{2}\b", "", huruf)

    # menghapus karakter Ä
    # huruf = huruf.encode('utf-8').decode('iso-8859-1')
    huruf = re.sub(r'‚Ä¶', '', huruf)

    # menghapus seluruh karakter pada string huruf yang tidak termasuk angka (0-9), 
    # huruf kecil (a-z), dan huruf besar (A-Z), dan menggantinya dengan spasi (' ')
    huruf = re.sub('[^0-9a-zA-Z]+', ' ', huruf)

    return huruf

# menghubungkan database
baca_db = sqlite3.connect('database.db', check_same_thread = False)
# membaca tabel kamus
tampil_tk = pd.read_sql_query('SELECT * FROM tkamus_alay', baca_db)
# membaca tabel abusive
tampil_ta = pd.read_sql_query('SELECT * FROM tkata_kasar', baca_db)
# untuk membuat sebuah kamus (dictionary) dari dua array/list yang berbeda
alay_dict = dict(zip(tampil_tk['kata_alay'], tampil_tk['kata_normal']))

# mengubah kata-kata alay dalam sebuah teks menjadi kata-kata normal 
# menggunakan kamus alay_dict yang telah dibuat sebelumnya.

def alay_to_normal(huruf):
    result = []
    for word in huruf.split(' '):
        if word in alay_dict:
            result.append(alay_dict[word])
        else:
            result.append(word)
    return ' '.join(result)

# untuk mengambil kolom 'kata_kasar' dari suatu dataframe (dalam hal ini tampil_ta), 
# kemudian mengonversi semua kata pada kolom tersebut menjadi huruf kecil (lowercase) dan 
# menyimpannya dalam sebuah list l_abusive.
l_abusive = tampil_ta['kata_kasar'].str.lower().tolist()

# untuk menghapus semua kata-kata kasar yang terdapat pada parameter huruf. 
# Fungsi ini menggunakan list l_abusive yang telah dibuat sebelumnya sebagai referensi 
# kata-kata kasar yang akan dihapus.
def normalize_abusive(huruf):
    list_word = huruf.split()
    return ' '.join([huruf for huruf in list_word if huruf not in l_abusive])

# menjalankan fungsi pembersihan
def text_cleansing(huruf):
    huruf = lowercase(huruf)
    huruf = perbaiki_kalimat(huruf)
    huruf = alay_to_normal(huruf)
    huruf = normalize_abusive(huruf)
    huruf = huruf.replace("gue", "saya")
    return huruf

# Mendefinisikan dokumentasi API yang digunakan
@swag_from("docs/input_data.yml", methods=['POST'])
# Mendefinisikan route atau URL endpoint pada web server
@app.route('/input_data', methods=['POST'])
def test():
    # Mengambil data input yang diterima melalui form dengan nama "input_data" pada request POST
    input_txt = str(request.form["input_data"])
    # Memanggil fungsi text_cleansing() dengan parameter input_txt dan menyimpan hasilnya ke dalam variabel output_txt
    output_txt = text_cleansing(input_txt)

    # Membuat koneksi ke database dan membuat tabel baru dengan nama "tinput_data" pada database jika belum ada
    # Menggunakan with statement untuk memastikan bahwa koneksi database ditutup setelah digunakan
    with sqlite3.connect("database.db") as baca_db:
        # Mengeksekusi query untuk membuat tabel baru dengan nama tinput_data jika tabel tersebut belum ada
        baca_db.execute('create table if not exists tinput_data (input_text varchar(255), output_text varchar(255))')
        # Membuat query SQL untuk memasukkan nilai input_txt dan output_txt ke dalam tabel tinput_data
        query_txt = 'insert into tinput_data (input_text , output_text) values (?,?)'
        val = (input_txt, output_txt)
        # Menjalankan query untuk memasukkan nilai input_txt dan output_txt ke dalam tabel tinput_data
        baca_db.execute(query_txt, val)
        # Menyimpan perubahan pada database
        baca_db.commit()

    # Membuat dictionary baru bernama return_txt yang berisi input_txt dan output_txt
    return_txt = { "input" :input_txt, "output" : output_txt}
    # Mengembalikan nilai dalam format JSON dari dictionary return_txt menggunakan fungsi jsonify dari library Flask
    return jsonify (return_txt)

# Menggunakan decorator untuk mengambil informasi dokumentasi API dari file upload_data.yml
@swag_from("docs/upload_data.yml", methods=['POST'])

# Menggunakan decorator untuk mendefinisikan route atau URL endpoint pada web server
@app.route('/upload_data', methods=['POST'])
def upload_file():

    # Mengambil file yang diupload melalui form dengan nama "upload_data" pada request POST
    file = request.files["upload_data"]

    # Membaca file CSV menggunakan Pandas dan menyimpan hasilnya ke dalam variabel df_csv
    df_csv = (pd.read_csv(file, encoding="latin-1"))

    # Mengaplikasikan fungsi text_cleansing() pada kolom 'Tweet' pada dataframe df_csv dan menyimpan hasilnya ke dalam kolom 'new_tweet'
    df_csv['new_tweet'] = df_csv['Tweet'].apply(text_cleansing)

    # Menyimpan dataframe df_csv ke dalam tabel 'clean_tweet' pada database menggunakan fungsi to_sql dari Pandas
    df_csv.to_sql("clean_tweet", con=baca_db, index=False, if_exists='append')

    # Menutup koneksi ke database
    baca_db.close()

    # Mengambil semua nilai dari kolom 'new_tweet' pada dataframe df_csv dan menyimpannya ke dalam variabel cleansing_tweet
    cleansing_tweet = df_csv.new_tweet.to_list()

    # Membuat dictionary baru bernama return_file yang berisi cleansing_tweet
    return_file = {
        'output': cleansing_tweet}

    # Mengembalikan nilai dalam format JSON dari dictionary return_file menggunakan fungsi jsonify dari library Flask
    return jsonify(return_file)

# Mengeksekusi aplikasi Flask jika kode dijalankan sebagai program utama
if __name__ == '__main__':
	app.run()