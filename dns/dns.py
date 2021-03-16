# pip3 install godaddypy

import urllib.request
import godaddypy
from logging_filter import logger
logging= logger

config = {
  "key"   : "",
  "secret": "",
  "domain": "",
  "host"  : "",
  "type"  : "A",
  "ttl"   : 600
}

def main():
  #logging.basicConfig(format='%(asctime)s%(levelname)s:%(message)s', level=logging.DEBUG)

  # Recover configuration
  api_key = config["key"]
  api_sec = config["secret"]
  domain  = config["domain"]
  host    = config["host"]
  type    = config["type"]
  ttl     = config["ttl"]

  # Create Godaddy account and client
  godaddy_account = godaddypy.Account(api_key=api_key, api_secret=api_sec)
  godaddy_client  = godaddypy.Client(godaddy_account)

  # Get current public IP address
  public_ip = urllib.request.urlopen('https://ident.me').read().decode('utf8')

  # Get current record
  records = godaddy_client.get_records(domain, record_type=type)
  # Get current IP address
  current_ip = records[0]["data"] #old: 1

  # If public and current address are equal, return
  if (current_ip == public_ip):
    logging.info("No update required; both IP addresses are the same (IP={})!".format(current_ip))
    return

  # Otherwise, set public address to current address
  result = godaddy_client.update_record_ip(public_ip, domain, host, type)
  if (result == False):
    logging.error("Error updating public IP address (IP={})!".format(current_ip))
  else:
    logging.error("Updated public IP address (IP={})!".format(public_ip))

if __name__ == "__main__":
  main()
