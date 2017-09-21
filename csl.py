"""This script takes actions on Splunk alert related to dynatrace agent
author : Suruchi Choudhary """

import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
import smtplib
import sys
import subprocess
import time

# third party modules
import requests

logging.basicConfig(filename='/log/csl_autoheal.log',level=logging.DEBUG)

# accepting host as command line argument
total = len(sys.argv)
print(total)
arglist = sys.argv
print(arglist)
host = arglist[1]
print(host)

# Global Variables
status_code = 200
system_time = datetime.datetime.now()
message = ["Here are the series of actions taken on host : {0}".format(host)]


def check_dt_url(host):
    # This method hits the healthcheck url and returns the status code
    print("Action: checking healthcheck url")
    message.append("Action: checking healthcheck url")
    logging.info("Action: checking healthcheck url")
    status = 0
    try:
        url = "http://{0}:8080/customer-shoppinglists-app".format(host)
        r = requests.head(url)
        status = r.status_code
        print(status)
        return status
    except requests.exceptions.ConnectionError as e:
        print("Exception occured !!!")
        return 500


def restart_tomcat():
    # This method restarts tomcat
    logging.info("Action: Starting tomcat")
    message.append("Action: Starting tomacat")
    print("Starting tomcat")
    p = subprocess.Popen('sudo service tomcat7 restart', stdout=subprocess.PIPE,
                          cwd='/app', shell=True)
    output = p.communicate()[0]
    print(output)
    time.sleep(20)


def send_email(message):
    # This method sends email with the log file as attachment
    logging.info("Sending email")
    msg = MIMEMultipart('alternative')
    s = smtplib.SMTP('smtp-gw1.wal-mart.com',25)
    toEmail = "skumaresan@walmart.com"
    fromEmail = "schoudhary@walmartlabs.com"
    msg['Subject'] = 'Autohealing tool from Splunk script'
    msg['From'] = fromEmail
    body = str(message)
    content = MIMEText(body, 'plain')
    filename = "/log/csl_autoheal.log"
    f = open(filename)
    attachment = MIMEText(f.read())
    attachment.add_header('Content-Disposition', 'attachment', filename=filename)
    msg.attach(attachment)
    msg.attach(content)
    s.sendmail(fromEmail, toEmail, msg.as_string())
    s.close()


# script flow starts here
healthcheck_status = check_dt_url()
if healthcheck_status != status_code:
    restart_tomcat()
    status_now = check_dt_url()
    if status_now != status_code:
        print("Restarted tomcat, but health check failed. "
              "Please check manually")
        logging.info("Restarted tomcat, but health check failed. "
                     "Please check manually")
        message.append("Restarted tomcat, but health check failed. "
                       "Please check manually")
else:
    print("Healthcheck is green. No Action taken")

send_email(message)
