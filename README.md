# iMessage-Attachment-Extractor
Extract your iMessage attachments on Mac

## Requirements 
* python3
* required packages

## Usage

    pip3 install -r requirements.txt

    python3 main.py [-h] [-v] [-f]


### Optional arguments:

* -h, --help: show this help message and exit

* -v, --verbose: Enable verbose output

* -f, --force_reload: Force iMessage database reload

### Process

1. Copy chat.db from '~/Library/Messages' to 'data/' folder 
2. Process database, and obtain message attachment locations
3. Move attachments (matching accepted_file_types) into 'output/thread/' folder, where 'thread' is the phone number of the thread the attachment is located
