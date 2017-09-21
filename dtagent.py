"""This script takes actions on Splunk alert related to dynatrace agent
author : Suruchi Choudhary """

import argparse
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
import smtplib
import sys
import subprocess
from subprocess import check_output

# third party modules
import requests

_DEFAULT_LOGGER_LEVEL = logging.WARN


class AutoHeal(object):
    def __init__(self):
        self.__init_logger()
        self.__init_vars(self)

    def __init_logger(self):
        name = self.__class__.__name__
        level = _DEFAULT_LOGGER_LEVEL
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        log_file = "/log/dynatrace_autoheal.log"
        handler = logging.FileHandler(log_file, mode='a+')
        handler.setLevel(level)
        format_string = "[%(levelname)s] %(asctime)s %(name)s - %(message)s"
        formatter = logging.Formatter(format_string)
        handler.setFormatter(formatter)
        root_logger = logging.getLogger()
        root_logger.addHandler(handler)
        root_logger.setLevel(level)
        self.logger.debug("Logger initialized: {0}".format(name))

    def __init_vars(self, host):
        self.host = host
        self.status_code = 200
        self.message = ["Here are the series of actions taken on host"
                        " : {0}".format(host)]

    def check_dt_url(self, host):
        # This method hits the healthcheck url and returns the status code
        print("Action: checking health check url")
        self.message.append("Action: checking health check url")
        self.logger.info("Action: checking health check url")
        try:
            url = "http://{0}:8080/dtagent_bootstrap.js".format(host)
            r = requests.head(url)
            status = r.status_code
            print(status)
            return status
        except requests.exceptions.ConnectionError as e:
            print("Exception occured !!! {0}").format(e)
            return 500

    def check_dt_pid(self):
        # This method checks process id of dynatrace agent
        self.logger.info("Action: Checking if Dynatrace agent is runing")
        self.message.append("Action: Checking if Dynatrace agent is runing")
        print("Checking if Dynatrace agent is runing")
        try:
            dt_pid = check_output(["pidof", 'dtwsagent'])
            print(dt_pid)
            return True
        except subprocess.CalledProcessError as e:
            print("Dynatrace agent is not running, couldn't get"
                  " process id. {0}".format(e))
            return False

    def start_dt_agent(self):
        # This method starts dynatrace agent
        self.logger.info("Action: Starting dynatrace agent")
        self.message.append("Action: Starting dynatrace agent")
        print("Starting dynatrace agent")
        try:
            p = subprocess.Popen([sys.executable,
                                  'sudo /app/configurations/dynatrace-6.2/'
                                  'agent/lib64/dtwsagent &'],
                                 stdout=subprocess.PIPE, cwd='/app',
                                 shell=True)
            output = p.communicate()[0]
            print(output)
        except subprocess.CalledProcessError as e:
            print('Exception occurred {0}'.format(e))
            self.logger.info('Exception occurred {0}'.format(e))
            self.message.append("Exception occurred {0} . "
                                "Couldn't start dynatrace agent. "
                                "Please check manually".format(e))
            sys.exit()

    def restart_apache(self):
        # This method restarts apache
        self.logger.info("Action: Starting apache")
        self.message.append("Action: Starting apache")
        print("Starting apache")
        p1 = subprocess.Popen('sudo service httpd restart',
                              stdout=subprocess.PIPE, cwd='/app', shell=True)
        output1 = p1.communicate()[0]
        print(output1)

    def send_email(self, message):
        # This method sends email with the log file as attachment
        message = self.message
        self.logger.info("Sending email")
        msg = MIMEMultipart('alternative')
        s = smtplib.SMTP('smtp-gw1.wal-mart.com', 25)
        to_email = ["skumaresan@walmart.com", "schoudhary@walmartlabs.com", "mmurahari@walmartlabs.com"]
        from_email = "nclb@walmartlabs.com"
        msg['Subject'] = 'Auto healing tool from dynatrace script'
        msg['From'] = from_email
        body = str(message)
        content = MIMEText(body, 'plain')
        filename = "/log/dynatrace_autoheal.log"
        f = open(filename)
        attachment = MIMEText(f.read())
        attachment.add_header('Content-Disposition', 'attachment',
                              filename=filename)
        msg.attach(attachment)
        msg.attach(content)
        s.sendmail(from_email, to_email, msg.as_string())
        s.close()

    def main(self):
        parser = argparse.ArgumentParser(
            description='host can be the fully qualified hostname '
                        'or the host ip address.')
        parser.add_argument('--host', help='pass fully '
                                           'qualified hostname or ip address')
        args = parser.parse_args()
        print(args.host)

        if self.check_dt_pid() is False:
            self.start_dt_agent()
            self.check_dt_pid()
            healthcheck_code = self.check_dt_url(self.host)
            if healthcheck_code != self.status_code:
                self.restart_apache()
                if self.check_dt_url(self.host) is self.status_code:
                    print("Health check is green")
                    self.logger.info("Health check is green")
                    self.message.append("Health check is green")
            else:
                print("Health check is green")
                self.logger.info("Health check is green")
                self.message.append("Health check is green")
        else:
            print("Everything is fine, No Action taken. "
                  "Please check manually if alert reoccurs")

        self.send_email(self.message)


if __name__ == '__main__':
    dt = AutoHeal()
    dt.main()

