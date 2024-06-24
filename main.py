import os
import subprocess
import asyncio
import json
import ssl
import time
import uuid
from loguru import logger
from websockets_proxy import Proxy, proxy_connect
import websockets
import argparse

WEBSOCKET_URLS = [
    "wss://proxy.wynd.network:4650",
    "wss://proxy.wynd.network:4444"
]

PING_INTERVAL = 3  # PING interval in seconds

def print_intro():
    print("════════════════════════════════════════════════════════════")
    print("║       Welcome to Grass B0T!!🦗                           ║")
    print("║                                                          ║")
    print("║     Follow us on Twitter:                                ║")
    print("║     https://twitter.com/cipher_airdrop                   ║")
    print("║                                                          ║")
    print("║     Join us on Telegram:                                 ║")
    print("║     - https://t.me/+tFmYJSANTD81MzE1                     ║")
    print("╚════════════════════════════════════════════════════════════")
    answer = input('Will you F** Grass Airdrop? (Y/N): ')
    if answer.lower() != 'y':
        print('Aborting installation.')
        exit(1)

def check_tmux():
    # Check if tmux is installed
    result = subprocess.run(['which', 'tmux'], stdout=subprocess.PIPE)
    if result.returncode != 0:
        print("tmux is not installed. Installing tmux...")
        subprocess.run(['sudo', 'apt-get', 'install', '-y', 'tmux'])

def manage_tmux_session(session_name):
    # Kill existing tmux session with the given name, if it exists
    subprocess.run(['tmux', 'kill-session', '-t', session_name], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
    
    # Create a new tmux session with the given name
    subprocess.run(['tmux', 'new-session', '-d', '-s', session_name])

def get_user_input():
    uid = input("Enter your Grass UID: ").strip()
    proxy_file = input("Enter the path to your proxy.txt file: ").strip()
    return uid, proxy_file

def load_proxies(proxy_file):
    proxies = []
    with open(proxy_file, 'r') as file:
        for line in file:
            ip, port, username, password = line.strip().split(':')
            proxies.append(f'socks5://{username}:{password}@{ip}:{port}')
    return proxies

async def connect_to_wss(socks5_proxy, user_id):
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    async def send_ping(websocket):
        while True:
            try:
                send_message = json.dumps({
                    "id": str(uuid.uuid4()),
                    "version": "1.0.0",
                    "action": "PING",
                    "data": {}
                })
                logger.debug(f"Sending PING message: {send_message}")
                await websocket.send(send_message)
                await asyncio.sleep(PING_INTERVAL)
            except websockets.exceptions.ConnectionClosed:
                logger.warning("WebSocket connection closed during ping, attempting to reconnect.")
                break
            except asyncio.CancelledError:
                logger.warning("Ping task was cancelled.")
                break

    for uri in WEBSOCKET_URLS:
        while True:
            try:
                proxy = Proxy.from_url(socks5_proxy)
                async with proxy_connect(uri, proxy=proxy, ssl=ssl_context, extra_headers={
                    "Origin": "chrome-extension://lkbnfiajjmbhnfledhphioinpickokdi",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
                }) as websocket:
                    logger.info(f"Connected to WebSocket URI: {uri}")

                    ping_task = asyncio.create_task(send_ping(websocket))

                    async for message in websocket:
                        message = json.loads(message)
                        logger.info(f"Received message: {message}")

                        if message.get("action") == "AUTH":
                            auth_response = json.dumps({
                                "id": message["id"],
                                "origin_action": "AUTH",
                                "result": {
                                    "browser_id": str(uuid.uuid4()),
                                    "user_id": user_id,
                                    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                                    "timestamp": int(time.time()),
                                    "device_type": "extension",
                                    "version": "4.20.2",
                                    "extension_id": "lkbnfiajjmbhnfledhphioinpickokdi"
                                }
                            })
                            logger.debug(f"Sending AUTH response: {auth_response}")
                            await websocket.send(auth_response)

                        elif message.get("action") == "PONG":
                            pong_response = json.dumps({
                                "id": message["id"],
                                "origin_action": "PONG"
                            })
                            logger.debug(f"Sending PONG response: {pong_response}")
                            await websocket.send(pong_response)
            except websockets.exceptions.ConnectionClosedOK:
                logger.info("WebSocket connection closed normally, attempting to reconnect.")
            except Exception as e:
                logger.error(f"Error connecting to WebSocket URI: {uri} - {e}")
                logger.error(f"Using proxy: {socks5_proxy}")
            await asyncio.sleep(5)  # wait before retrying

async def main(user_id, socks5_proxy_list):
    tasks = [connect_to_wss(proxy, user_id) for proxy in socks5_proxy_list]
    await asyncio.gather(*tasks)

if __name__ == '__main__':
    # If running in tmux, parse arguments
    if 'TMUX' in os.environ:
        parser = argparse.ArgumentParser()
        parser.add_argument('--user-id', type=str, required=True)
        parser.add_argument('--proxy-file', type=str, required=True)
        args = parser.parse_args()

        # Run the main function
        asyncio.run(main(args.user_id, load_proxies(args.proxy_file)))
    else:
        print_intro()
        check_tmux()
        manage_tmux_session('GrassV2')
        user_id, proxy_file = get_user_input()
        
        # Start the script in the tmux session
        command = f'python3 {__file__} --user-id {user_id} --proxy-file {proxy_file}'
        subprocess.run(['tmux', 'send-keys', '-t', 'GrassV2', command, 'C-m'])
