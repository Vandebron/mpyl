"""Jenkins multi-branch pipeline runner"""
import datetime
import os
import signal
import sys
import time
from dataclasses import dataclass

import requests
from jenkinsapi.build import Build
from jenkinsapi.custom_exceptions import JenkinsAPIException
from jenkinsapi.jenkins import Jenkins
from jenkinsapi.job import Job
from rich.errors import MarkupError
from rich.progress import Progress
from rich.prompt import Confirm
from rich.status import Status
from rich.text import Text

from . import Pipeline


def stream_utf_8_logs(self, interval=0):
    """
    Return generator which streams parts of text console.
    Workaround for https://github.com/pycontribs/jenkinsapi/pull/843
    """
    url = f"{self.baseurl}/logText/progressiveText"
    size = 0
    more_data = True
    while more_data:
        resp = self.job.jenkins.requester.get_url(
            url, params={"start": size}
        )
        content = resp.content
        if content:
            if isinstance(content, str):
                yield content
            elif isinstance(content, bytes):
                yield content.decode(resp.encoding)
            else:
                raise JenkinsAPIException(
                    "Unknown content type for console"
                )
        size = resp.headers["X-Text-Size"]
        more_data = resp.headers.get("X-More-Data")
        time.sleep(interval)


Build.stream_utf_8_logs = stream_utf_8_logs


@dataclass
class JenkinsRunner:
    pipeline: Pipeline
    jenkins: Jenkins
    status: Status

    def get_job(self, name: str) -> Job:
        try:
            return self.jenkins.get_job(name)
        except KeyError:
            self.status.update(f'Job for {self.pipeline.human_readable()} not found. This could take a while. '
                               'Triggering build scan...')
            requests.post(f'{self.pipeline.pipeline_location()}/build?delay=0#',
                          auth=(self.jenkins.username, self.jenkins.password), timeout=10)

            while True:
                try:
                    self.jenkins.jobs_container = None  # force update of job info
                    return self.jenkins.get_job(name)
                except KeyError:
                    self.status.update(f'Waiting for {self.pipeline.human_readable()} to appear...')
                    time.sleep(1)

    def await_parameter_build(self, build_job: Job):
        queue = build_job.invoke()
        param_build = queue.block_until_building(delay=3)
        self.status.console.log(f'Build in Jenkins {queue.get_build().get_build_url()}')
        self.status.update('Running initial build to set parameters. This may take a minute..')
        while build_job.is_running():
            time.sleep(1)
        self.status.console.log('Build parameters retrieved')

        if not param_build.is_good:
            self.status.console.log(f"⚠️ Failed to get parameters: {param_build.get_build_url()}")
            sys.exit()

    @staticmethod
    def to_icon(build_result: Build) -> str:
        return '✅ ' if build_result.is_good() else '❌ '

    def follow_logs(self, job: Job, build_number: int, duration_estimation: int):
        self.status.update("Waiting for logs....")
        while job.get_last_buildnumber() != build_number:
            time.sleep(1)
        self.status.stop()

        build_to_follow: Build = job.get_build(build_number)
        self.status.console.log(f'{build_to_follow} {self.pipeline.build_location()}')

        with Progress(console=self.status.console) as progress:
            build_task = progress.add_task("", total=duration_estimation, visible=duration_estimation > 0)
            start_time = time.time()

            def cancel_handler(_sig, _frame):
                progress.stop()
                stop_build = Confirm.ask("Stop build?")
                if stop_build:
                    build_to_follow.stop()

            signal.signal(signal.SIGINT, cancel_handler)
            for line in build_to_follow.stream_utf_8_logs():
                current_time = time.time()
                elapsed_time = current_time - start_time
                lines = line.rstrip().split('\n')

                try:
                    text = "".join(lines)
                    progress.log(Text.from_ansi(text))
                except MarkupError:
                    progress.log("Could not render log line")
                progress.update(build_task, completed=elapsed_time)
            progress.update(build_task, completed=duration_estimation)

        build_to_follow.block_until_complete()
        finished_build = job.get_last_build()
        self.status.console.log(
            f'[link={finished_build.get_build_url()}][i]Build[/link] for {self.pipeline.human_readable()} '
            f'ended with outcome {self.to_icon(finished_build)}', markup=True)
        self.status.console.log()

        os.system('afplay /System/Library/Sounds/' + ('Glass.aiff' if finished_build.is_good() else 'Sosumi.aiff'))
        sys.exit()

    def run(self, pipeline_parameters: dict):
        job: Job = self.get_job(self.pipeline.job_name())
        if not list(job.get_build_ids()):
            self.await_parameter_build(job)

        build = job.get_last_build()
        last_build_number = build.get_number()
        if job.is_running():
            self.status.console.log(
                f"Build {last_build_number} 🏗️ for {self.pipeline.human_readable()} is still running.")
            self.status.console.log(f"{build.get_build_url()}")
            self.follow_logs(job, last_build_number, 0)

        self.status.update("Starting build...")

        last_build = 0

        self.jenkins.build_job(self.pipeline.job_name(), params=pipeline_parameters)

        if last_build_number > 1:
            last_build = build.get_duration().seconds
            self.status.console.log(f'Last build {last_build_number} {self.to_icon(build)} took'
                                    f' {str(datetime.timedelta(seconds=last_build))}')

        new_build_number = last_build_number + 1

        self.follow_logs(job, new_build_number, last_build)
