"""This script takes actions on Splunk alert when Splunk Forwarders are down
author: Suruchi Choudhary """

import argparse
import datetime
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging, logging.handlers
import smtplib
import subprocess
import time

# third party modules
import requests


_DEFAULT_LOGGER_LEVEL = logging.INFO
_SYSTEM_TIME = datetime.datetime.now()
_LOG_DIR = "/log"


class AutoHeal(object):
    def __init__(self):
        self.__init_logger()
        self.__init_vars(self)

    def __init_logger(self):
        name = self.__class__.__name__
        level = _DEFAULT_LOGGER_LEVEL
        format_string = "[%(levelname)s] %(asctime)s %(name)s - %(message)s"
        formatter = logging.Formatter(format_string)
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        # File Handler
        log_file_name = _SYSTEM_TIME.strftime('splunk_autoheal_%H:%M_%d_%m_%Y.log')
        self.log_file = os.path.join(_LOG_DIR, log_file_name)
        print(self.log_file)
        file_handler = logging.handlers.RotatingFileHandler(self.log_file, mode='a+')
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        # Console Handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

    def __init_vars(self, host):
        self.host = host
        self.status_code = 200
        self.message = ["Here are the series of actions taken on host"]

    def restart_jboss(self):
        # This method restarts jboss and prints the console output
        self.message.append("Action: restarting jboss")
        print("Action: restarting jboss")
        self.logger.info("Action: restarting jboss")
        p = subprocess.Popen('sudo service jboss-container restart',
                             stdout=subprocess.PIPE,
                             cwd='/app', shell=True)
        output = p.communicate()[0]
        print(output)
        self.logger.info(output)

    def check_splunk_status(self):
        # This method checks returns True if splunk agent is running
        print("Action: checking splunk status")
        self.message.append("Action: checking splunk status")
        self.logger.info("Action: checking splunk status")
        p = subprocess.Popen('sudo /app/splunkforwarder/bin/splunk status',
                             stdout=subprocess.PIPE,
                             cwd='/app/splunkforwarder/bin/', shell=True)
        output = p.communicate()[0]
        result = output.decode("utf-8")
        print(result[:18])
        req_status = "splunkd is running"
        if req_status in str(result[:18]):
            self.logger.info(req_status)
            return True
        else:
            return False

    def check_url_health(self, host):
        # This method hits the healthcheck url and returns the status code
        print("Action: checking healthcheck url")
        self.logger.info("Action: checking healthcheck url")
        try:
            url = "http://{0}:8080/asda-estore/healthcheck/testenv.jsp".format(host)
            print(url)
            r = requests.head(url)
            status = r.status_code
            print(status)
            self.logger.info(status)
            return status
        except requests.exceptions.ConnectionError as e:
            print("in except block : {0}".format(e))
            self.logger.info("in except block : {0}".format(e))
            return 500

    def send_email(self):
        # This method sends email with the log file as attachment
        self.logger.info("Sending email")
        outer = MIMEMultipart('alternative')
        server = smtplib.SMTP('smtp-gw1.wal-mart.com', 25)
        recipients = ['skumaresan@walmart.com', 'schoudhary@walmartlabs.com', 'MMurahari@walmartlabs.com']
        # to_email = "schoudhary@walmartlabs.com"
        from_email = "nclb@walmartlabs.com"
        outer['Subject'] = 'Auto healing when "Splunk Forwarders or instances may be down" alert triggers'
        outer['From'] = from_email
        outer['To'] = ", ".join(recipients)
        outer['Date'] = time.ctime()
        f = open(self.log_file, 'r')
        msg = MIMEText(f.read())
        attachment = MIMEText(f.read())
        attachment.add_header('Content-Disposition', 'attachment',
                              filename=self.log_file)
        outer.attach(attachment)
        f.close()
        outer.attach(msg)
        server.sendmail(from_addr=from_email, to_addrs=recipients, msg=outer.as_string())
        server.close()

    def main(self):
        parser = argparse.ArgumentParser(
            description='host can be the fully qualified hostname '
                        'or the host ip address.')
        parser.add_argument('--host', help='pass fully '
                                           'qualified hostname or ip address',
                            required=True)
        args = parser.parse_args()
        self.logger.info("{0} : {1}".format(self.message, args.host))
        # self.message.append(args.host)
        print(args.host)

        if self.check_splunk_status():
            self.logger.info("No Action taken as Splunk is up. Check whether server.log file exists and/or jboss instance is up.")
        else:
            self.logger.info("Splunk agent is down, starting it....")
            print("Splunk agent is down, starting it....")
            self.logger.info("Splunk agent is down....")
            self.logger.info("Action: Starting Splunk Agent")
            p = subprocess.Popen('sudo /app/splunkforwarder/bin/splunk start',
                                 stdout=subprocess.PIPE,
                                 cwd='/app/splunkforwarder/bin/', shell=True)
            output = p.communicate()[0]
            self.logger.info(output)

        if os.path.isfile("/log/server.log") is False:
            print("couldn't find server.log")
            self.logger.info("couldn't find server.log")
            self.restart_jboss()
            time.sleep(120)
            healthcheck_code = self.check_url_health(args.host)
            if self.status_code != healthcheck_code:
                self.logger.info("Restarted jboss, waited for 2 minutes, "
                                    "Testenv.jsp is still failing. "
                                    "Please check the host health manually")
            else:
                self.logger.info("Successfully Restarted jboss")
        else:
            self.logger.info("Found server.log file")
            print("Found server.log file")
            healthcheck_code = self.check_url_health(args.host)
            print(healthcheck_code)
            if self.status_code != healthcheck_code:
                self.restart_jboss()
                time.sleep(120)
                healthcheck_code = self.check_url_health(args.host)
                if self.status_code != healthcheck_code:
                    self.logger.info("Restarted jboss, waited for 2 minutes"
                                        ", Testenv.jsp is still failing. "
                                        "Please check the host health manually")
                else:
                    self.logger.info("Successfully Restarted jboss")
            else:
                self.logger.info("Healthcheck is green, NO action taken")
                print("Healthcheck is green, NO action taken")

        self.send_email()


if __name__ == '__main__':
    sp = AutoHeal()
    sp.main()
