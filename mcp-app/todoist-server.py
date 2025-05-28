from dataclasses import dataclass
import logging
import os
import sys
from typing import Literal, Optional
from dotenv import load_dotenv
import requests
import datetime

from mcp.server.fastmcp import FastMCP
from todoist_api_python.api import TodoistAPI

load_dotenv()

TODOIST_API_TOKEN = os.getenv("TODOIST_API_TOKEN")
todoist_api = TodoistAPI(TODOIST_API_TOKEN)
mcp = FastMCP("todoist-server", dependencies=["todoist_api_python"])
logger = logging.getLogger("todoist_server")

base_url = "https://api.todoist.com/rest/v2/"
header = {'Authorization': f'Bearer {TODOIST_API_TOKEN}'}
sync_url = "https://api.todoist.com/sync/v9/"
time_period = 6


@dataclass
class Project:
    id: str
    name: str


# Abstraction for Todoist project
# https://developer.todoist.com/rest/v2/#get-all-projects
@dataclass
class TodoistProjectResponse:
    id: str
    name: str


def date_difference(date1: str, date2: str) -> int:
    """Compare two dates in the format 'YYYY-MM-DD'"""
    date1 = datetime.strptime(date1, "%Y-%m-%d")
    date2 = datetime.strptime(date2, "%Y-%m-%d")
    return (date1 - date2).days


@mcp.tool()
def get_projects() -> list[Project]:
    """Get all todo projects. These are like folders for tasks in Todoist"""
    try:
        projects: TodoistProjectResponse = todoist_api.get_projects()
        return [Project(p.id, p.name) for p in projects]
    except Exception as e:
        return f"Error: Couldn't fetch projects {str(e)}"


def get_project_id_by_name(project_name: str) -> str:
    """Search for a project by name and return its ID"""
    projects = get_projects()
    for project in projects:
        if project.name.lower() == project_name.lower():
            return project.id
    return None


@mcp.tool()
def get_tasks(
    project_id: Optional[str] = None,
    project_name: Optional[str] = None,
    task_name: Optional[str] = None,
    labels: Optional[list[str]] = None,
    due_date: Optional[str] = None,
    is_overdue: Optional[bool] = None,
    priority: Optional[Literal[1, 2, 3, 4]] = None,
    limit: Optional[int] = None,
) -> list[str]:
    """
    Fetch user's tasks. These can be filtered by project, labels, time, etc.
    If no filters are provided, all tasks are returned.

    Args:
    - project_id: The string ID of the project to fetch tasks from. Example
     '1234567890'
    - project_name: Name of the project to fetch tasks from. Example 'Work' or
      'Inbox'
    - task_name: Filter tasks by name. Example 'Buy groceries'
    - labels: List of tags used to filter tasks.
    - priority: Filter tasks by priority level. 4 (urgent), 3 (high), 2 (
      normal), 1 (low)
    - due_date: Specific due date in YYYY-MM-DD format. Example '2021-12-31'
    - is_overdue: Filter tasks that are overdue.
    - limit: Maximum number of tasks to return. Default is all.
    """
    tasks = todoist_api.get_tasks()

    # How to implement "did you mean this project?" feature?
    if project_name:
        project_id = get_project_id_by_name(project_name)
        if not project_id:
            raise ValueError(f"Project '{project_name}' not found")

    if project_id:
        project_id = project_id.strip('"')
        tasks = [t for t in tasks if t.project_id == project_id]

    if task_name:
        tasks = [t for t in tasks if task_name.lower() in t.content.lower()]

    if due_date:
        tasks = [t for t in tasks if t.due and t.due["date"] == due_date]

    if is_overdue is not None:
        now = datetime.today().strftime("%Y-%m-%d")
        tasks = [
            t for t in tasks if t.due and
            (date_difference(now, t.due["date"]) < 0) == is_overdue
        ]

    if labels:
        for label in labels:
            tasks = [t for t in tasks if label.lower() in
                     [lb.lower() for lb in t.labels]]

    if priority:
        tasks = [t for t in tasks if t.priority == priority]

    return [{"id": t.id, "title": t.content} for t in tasks][:limit]


@mcp.tool()
def delete_task(task_id: str):
    """Delete a task by its ID"""
    try:
        task_id = task_id.strip('"')
        is_success = todoist_api.delete_task(task_id=task_id)
        if not is_success:
            raise Exception
        return "Task deleted successfully"
    except Exception as e:
        raise Exception(f"Couldn't delete task {str(e)}")


@mcp.tool()
def create_task(
    content: str,
    description: Optional[str] = None,
    project_id: Optional[str] = None,
    labels: Optional[list[str]] = None,
    priority: Optional[int] = None,
    due_date: Optional[str] = None,
    section_id: Optional[str] = None,
) -> str:
    """
    Create a new task

    Args:
    - content [str]: Task content. This value may contain markdown-formatted
      text and hyperlinks. Details on markdown support can be found in the
      Text Formatting article in the Help Center.
    - description [str]: A description for the task. This value may contain
      markdown-formatted text and hyperlinks. Details on markdown support can
      be found in the Text Formatting article in the Help Center.
    - project_id [str]: The ID of the project to add the task. If none, adds
      to user's inbox by default.
    - labels [list[str]]: The task's labels (a list of names that may
      represent either personal or shared labels).
    - priority [int]: Task priority from 1 (normal) to 4 (urgent).
    - due_date [str]: Specific date in YYYY-MM-DD format relative to user’s
      timezone.
    - section_id [str]: The ID of the section to add the task to

    Returns:
    - task_id: str:
    """
    try:
        data = {}
        if description:
            data["description"] = description
        if project_id:
            data["project_id"] = project_id
        if labels:
            if isinstance(labels, str):
                labels = [labels]
            data["labels"] = labels
        if priority:
            data["priority"] = priority
        if due_date:
            data["due_date"] = due_date
        if section_id:
            data["section_id"] = section_id

        task = todoist_api.add_task(content, **data)
        return task.id
    except Exception as e:
        raise Exception(f"Couldn't create task {str(e)}")


@mcp.tool()
def update_task(
    task_id: str,
    content: Optional[str] = None,
    description: Optional[str] = None,
    labels: Optional[list[str]] = None,
    priority: Optional[int] = None,
    due_date: Optional[str] = None,
    deadline_date: Optional[str] = None,
):
    """
    Update an attribute of a task given its ID. Any attribute can be updated.

    Args:
    - task_id [str | int]: The ID of the task to update. Example '1234567890'
      or 1234567890
    - content [str]: Task content. This value may contain markdown-formatted
      text and hyperlinks. Details on markdown support can be found in the
      Text Formatting article in the Help Center.
    - description [str]: A description for the task. This value may contain
      markdown-formatted text and hyperlinks. Details on markdown support can
      be found in the Text Formatting article in the Help Center.
    - labels [list[str]]: The task's labels (a list of names that may
      represent either personal or shared labels).
    - priority [int]: Task priority from 1 (normal) to 4 (urgent).
    - due_date [str]: Specific date in YYYY-MM-DD format relative to user’s
      timezone.
    - deadline_date [str]: Specific date in YYYY-MM-DD format relative to
      user’s timezone.
    """

    # Client sometimes struggle to convert int to str
    task_id = task_id.strip('"')
    try:
        data = {}
        if content:
            data["content"] = content
        if description:
            data["description"] = description
        if labels:
            if isinstance(labels, str):
                labels = [labels]
            data["labels"] = labels
        if priority:
            data["priority"] = priority
        if due_date:
            data["due_date"] = due_date
        if deadline_date:
            data["deadline_date"] = deadline_date

        is_success = todoist_api.update_task(task_id=task_id, **data)
        if not is_success:
            raise Exception

        return "Task updated successfully"
    except Exception as e:
        raise Exception(f"Couldn't update task {str(e)}")


@mcp.tool()
def complete_task(task_id: str) -> str:
    """Mark a task as done"""
    try:
        task_id = task_id.strip('"')
        is_success = todoist_api.close_task(task_id=task_id)
        if not is_success:
            raise Exception
        return "Task closed successfully"
    except Exception as e:
        raise Exception(f"Couldn't close task {str(e)}")


def sync_helper(method, url, headers=header):
    resp = requests.request(method, url, headers=headers)
    if resp.status_code == 200:
        return dict(resp.json())
    resp.raise_for_status
    return resp.ok


def get_time(time_period):
    # setting start time at 6 days before the execution of this script
    today = datetime.date.today()
    last_week = today - datetime.timedelta(time_period)
    return (last_week.isoformat()+"T01:00")


@mcp.tool()
def get_completed_tasks():
    """Get completed tasks from the last 6 days.
       Args: time_period: int
       Returns: list[dict]: List of completed tasks
       """

    search_period = get_time(time_period)
    completed_items = (sync_helper('GET',
                                   sync_url +
                                   f'completed/get_all?since={search_period}'))

    return completed_items


def main():
    """Entry point for the installed package"""
    print("...", file=sys.stderr)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
