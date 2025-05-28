#!/usr/bin/env python

import requests
import os
from dotenv import load_dotenv
import datetime
from console import console
from rich.table import Table
import click
import pandas as pd
# from pprint import pprint

load_dotenv()


base_url = "https://api.todoist.com/rest/v2/"
header = {'Authorization': f'Bearer {os.getenv("todoist_token")}'}
sync_url = "https://api.todoist.com/sync/v9/"
time_period = 6


def get_task_information(notable_task):
    # pprint(notable_task)
    new_task = notable_task.replace('@OSN', '')
    task_content = new_task.split("@")
    return task_content


def get_time(time_period):
    # setting start time at 6 days before the execution of this script
    today = datetime.date.today()
    last_week = today - datetime.timedelta(time_period)
    return (last_week.isoformat()+"T01:00")


def rest_helper(method, url, headers=header):
    resp = requests.request(method, url, headers=headers)
    print(resp.json())


def sync_helper(method, url, headers=header):
    resp = requests.request(method, url, headers=headers)
    if resp.status_code == 200:
        return dict(resp.json())
    resp.raise_for_status
    return resp.ok


def convert_iso_month_day(isodate):
    dt = datetime.datetime.fromisoformat(isodate)
    return str(dt.month) + ' - ' + str(dt.day)


@click.command()
@click.option('--sort', default='Date',
              help='choose to sort by "date" or "account"')
def get_completed_items(sort):
    n_table = Table(title="Notables", show_lines=True)
    n_table.add_column("Account", style="cyan", no_wrap=True)
    n_table.add_column("Task", style="magenta")
    n_table.add_column("Date", style="magenta")
    sync_url = "https://api.todoist.com/sync/v9/"
    search_period = get_time(time_period)
    completed_items = (sync_helper('GET',
                                   sync_url +
                                   f'completed/get_all?since={search_period}'))
    df = pd.DataFrame(columns=["Account", "Task", "Date"])
    for x, v in completed_items.items():
        if x == 'items':
            for c_tasks in v:
                # pprint(c_tasks)
                # pprint(c_tasks)
                if '@OSN' in c_tasks['content']:
                    task_info = get_task_information(c_tasks['content'])
                    # n_table.add_row(
                    Account = task_info[-1].rstrip()
                    Task = task_info[0]
                    Date = convert_iso_month_day(c_tasks['completed_at'])
                    df = pd.concat([pd.DataFrame([[Account, Task, Date]],
                                   columns=df.columns), df],
                                   ignore_index=True)
    df = df.sort_values(by=[f"{sort}"])
    for index, row in df.iterrows():
        n_table.add_row(*row.astype(str).tolist())
    console.print(n_table)


if __name__ == "__main__":
    get_completed_items()
