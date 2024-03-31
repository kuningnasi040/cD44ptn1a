import requests
import threading
import colorama
import datetime
import time
from colorama import Fore, Style
from colorama import init
import sys

init(autoreset=True)

# Fungsi untuk membaca API key dari file key.txt
def read_api_key():
    try:
        with open("key.txt", "r") as key_file:
            return key_file.read().strip()
    except FileNotFoundError:
        print("File key.txt tidak ditemukan.")
        sys.exit(1)

# Fungsi untuk mendapatkan nomor telepon sementara
def get_phone_number(api_key, service_id, country_code, operator):
    number_url = f'https://smshub.org/stubs/handler_api.php?action=getNumber&api_key={api_key}&service={service_id}&country={country_code}&operator={operator}&forward=0'
    response = requests.get(number_url)
    number_info = response.text.strip()
    
    if ':' in number_info:
        number_id = number_info.split(':')[1]
        number = number_info.split(':')[2]
        return number_id, number
    else:
        print(f'Error: Respons tidak memiliki format yang benar: {number_info}')
        return None, None

# Fungsi untuk memeriksa status nomor telepon sementara
def check_number_status(api_key, number_id):
    status_url = f'https://smshub.org/stubs/handler_api.php?api_key={api_key}&action=getStatus&id={number_id}'
    response = requests.get(status_url)
    status = response.text.strip()
    return status

# Fungsi untuk memeriksa saldo pada akun SMSHub
def check_balance(api_key):
    balance_url = f'https://smshub.org/stubs/handler_api.php?api_key={api_key}&action=getBalance'
    response = requests.get(balance_url)
    if response.status_code == 200:
        try:
            balance_data = response.text.strip().split(':')
            if len(balance_data) == 2 and balance_data[0] == 'ACCESS_BALANCE':
                balance = float(balance_data[1])
                return balance
            else:
                print(f'Error: Respons tidak valid. Data saldo tidak ditemukan.')
                return None
        except ValueError:
            print(f'Error: Gagal mendapatkan saldo. Respons tidak valid.')
            return None
    else:
        print(f'Error: Gagal mendapatkan saldo. Kode status: {response.status_code}')
        return None

# Konfigurasi
service_id = 'ni'
country_code = '6'
operator = 'ANY'
running = True
previous_status = ""

# Membaca API key
api_key = read_api_key()

# Mendapatkan saldo dan mengonversi ke IDR
rub_to_idr_exchange_rate = 156
balance_rub = check_balance(api_key)
if balance_rub is not None:
    balance_idr = balance_rub * rub_to_idr_exchange_rate

# Fungsi utama untuk menampilkan informasi dan menjalankan loop
def main_loop():
    global running
    global previous_status
    print(Style.BRIGHT + '\n-------------------------------')
    print(Style.BRIGHT + '\nSMSHub OTP | Gojek IDR')
    balance = check_balance(api_key)
    sekarang = datetime.datetime.now()
    batas_waktu = sekarang + datetime.timedelta(hours=0, minutes=20)
    if balance is not None:
        print(f"\nSaldo SMSHub: {Fore.YELLOW}{balance} Rub | Rp.{balance_idr}")
        print(Fore.LIGHTBLACK_EX + "[TEKAN ENTER / CTRL+C UNTUK EXIT]\n")
        print('Timeout  :', batas_waktu.strftime("%H:%M:%S"))

        country_mapping = {
            '6': 'Indonesia',
            '151': 'Chille',
        }
        country_name = country_mapping.get(country_code, 'Unknown')

    running = True
    while running:
        number_id, number = get_phone_number(api_key, service_id, country_code, operator)
        if number_id and number:
            print(f'Country  : {country_name}')
            print(f'Operator : {operator}')
            print(f'Services : {service_id}')
            print(f'Nomor HP : {Fore.YELLOW}{number[:0] + number[1+1:]}')
            while running:
                inbox_url = f'https://smshub.org/stubs/handler_api.php?action=getInbox&api_key={api_key}&id={number_id}'
                inbox_response = requests.get(inbox_url)
                
                if inbox_response.status_code == 200:
                    try:
                        inbox_data = inbox_response.json()
                        for message in inbox_data:
                            print(f'Pesan masuk: {message["text"]}')
                    except ValueError:
                        None
                status = check_number_status(api_key, number_id)
                
                status_parts = status.split(':')
                if len(status_parts) > 1:
                    status = status_parts[0]
                    status_detail = ":".join(status_parts[1:])  # Gabungkan kembali detail status
                    print(f'OTP      : {Fore.GREEN}{status_detail}')
                
                if status == 'STATUS_OK':
                    resend_url = f'https://smshub.org/stubs/handler_api.php?api_key={api_key}&action=setStatus&status=3&id={number_id}'
                    response = requests.get(resend_url)
                    if response.status_code == 200:
                        print(f"OTP      : {Fore.YELLOW}SUCCES_RESEND")
                    else:
                        print(f'FAILED. {response.status_code}')
                
                if status == 'STATUS_CANCEL':
                    print(f'OTP      : {Fore.RED}CANCELED')
                    running = False
                    break 
                elif status != previous_status:
                    print(f'OTP      : {status}')
                    previous_status = status

# Membuat dan memulai thread utama
main_thread = threading.Thread(target=main_loop)
main_thread.start()

# Menunggu input dari pengguna untuk keluar
input('')
running = False
main_thread.join()
