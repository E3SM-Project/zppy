import os

import jinja2
from configobj import ConfigObj

from zppy.bundle import Bundle
from zppy.utils import get_tasks

TEMPLATE_DIR = os.path.join("zppy", "templates")

# A rendering context covering every parameter the header uses.
BASE_CONTEXT = {
    "machine": "chrysalis",
    "prefix": "my_task",
    "account": "my_account",
    "nodes": 1,
    "scriptDir": "/script/dir",
    "walltime": "01:00:00",
    "reservation": "",
    "partition": "debug",
    "qos": "regular",
    "constraint": "",
    "mail_type": "",
    "mail_user": "",
}


def render_header(**overrides):
    template_loader = jinja2.FileSystemLoader(searchpath=TEMPLATE_DIR)
    template_env = jinja2.Environment(loader=template_loader)
    template = template_env.get_template("inclusions/slurm_header.bash")
    context = dict(BASE_CONTEXT)
    context.update(overrides)
    return template.render(**context)


def test_slurm_header_without_mail_parameters():
    # The mail parameters are off by default, so they must not change the
    # generated scripts at all -- not even by adding blank lines. Otherwise,
    # every expected file of the integration tests would have to be
    # regenerated.
    expected = """
# Running on chrysalis

#SBATCH  --job-name=my_task
#SBATCH  --account=my_account
#SBATCH  --nodes=1
#SBATCH  --output=/script/dir/my_task.o%j
#SBATCH  --exclusive
#SBATCH  --time=01:00:00


#SBATCH  --partition=debug

"""
    assert render_header() == expected


def test_slurm_header_with_mail_parameters():
    actual = render_header(mail_type="BEGIN,END,FAIL", mail_user="me@example.com")
    assert "#SBATCH  --mail-type=BEGIN,END,FAIL\n" in actual
    assert "#SBATCH  --mail-user=me@example.com\n" in actual
    # Either parameter can be used on its own.
    assert "--mail-user" not in render_header(mail_type="FAIL")
    assert "--mail-type" not in render_header(mail_user="me@example.com")


def test_mail_type_set_on_a_task_section():
    # `mail_type`/`mail_user` are only in the `[default]` configspec, so
    # configobj does not validate them when they are set on a task section.
    # An unquoted comma-separated value arrives as a list there; `get_tasks`
    # must turn it back into a string, or the header would get
    # `--mail-type=['BEGIN', 'END', 'FAIL']`.
    config = ConfigObj(
        [
            "[default]",
            "active = True",
            "case = my_case",
            'mail_type = ""',
            'mail_user = ""',
            "[e3sm_diags]",
            "mail_type = BEGIN,END,FAIL",
            'mail_user = "me@example.com"',
        ]
    )
    tasks = get_tasks(config, "e3sm_diags")
    assert len(tasks) == 1
    assert tasks[0]["mail_type"] == "BEGIN,END,FAIL"
    assert tasks[0]["mail_user"] == "me@example.com"


def test_bundle_header_gets_mail_parameters(tmp_path):
    # A bundle builds its own rendering context rather than using the task
    # dict, so the mail parameters have to be threaded through `Bundle`
    # explicitly. A bundle takes them from the first task added to it.
    bundle_context = dict(BASE_CONTEXT)
    bundle_context.update(
        {
            "bundle": "bundle1",
            "dry_run": False,
            "debug": False,
            "environment_commands": "",
            "scriptDir": str(tmp_path),
            "mail_type": "END,FAIL",
            "mail_user": "me@example.com",
        }
    )
    bundle = Bundle(bundle_context)
    config = ConfigObj(
        [
            "[default]",
            "machine = chrysalis",
            "account = my_account",
            f"templateDir = {TEMPLATE_DIR}",
        ]
    )
    bundle.render(config)
    with open(bundle.bundle_file, "r") as f:
        rendered = f.read()
    assert "#SBATCH  --mail-type=END,FAIL\n" in rendered
    assert "#SBATCH  --mail-user=me@example.com\n" in rendered
