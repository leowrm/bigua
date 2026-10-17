from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from buiga_utils import *

def start():
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        func=gerar_cobranças, 
        trigger=CronTrigger.from_crontab("0 1 * * *"),
        id='1'
    )
    scheduler.add_job(
        func=verificar_cobrancas_atrasadas, 
        trigger=CronTrigger.from_crontab("*/5 * * * *"),
        id='2'
    )
    if not scheduler.running:
        scheduler.start()
