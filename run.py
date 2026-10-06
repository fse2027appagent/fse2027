import argparse
import os
import sys

from scripts.utils import print_with_color

if __name__ == "__main__":
    arg_desc = "AppAgent - deployment phase"
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter, description=arg_desc)
    parser.add_argument("--app")
    # 默认将每次运行的全部截图、日志和 token 统计存入项目的 result/
    # 目录；调用方仍可通过 --root_dir 覆盖该位置。
    default_result_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "result")
    parser.add_argument("--root_dir", default=default_result_dir)
    parser.add_argument("--app_description")
    parser.add_argument("--task")
    args = vars(parser.parse_args())

    app = args["app"]
    root_dir = args["root_dir"]
    app_desc = args["app_description"]
    task = args["task"]

    print_with_color("Welcome to the deployment phase of AppAgent!\nBefore giving me the task, you should first tell "
                     "me the name of the app you want me to operate and what documentation base you want me to use. I "
                     "will try my best to complete the task without your intervention. First, please enter the main "
                     "interface of the app on your phone and provide the following information.", "yellow")

    if not app:
        print_with_color("What is the name of the target app?", "blue")
        app = "meituan"
        app = app.replace(" ", "%_space")

    if not app_desc:
        print_with_color("Please simply describe the target app", "blue")
        app_desc = "a commonly used app for searching local merchants"
        app_desc = app_desc.replace(" ", "%_space")

    if not task:
        print_with_color("Please enter the description of the task you want me to complete in a few sentences:", "blue")
        task = 'look up "HeyTea" and leave a 5-star review '
        task = task.replace(" ", "%_space")

    android_home = os.environ.get("ANDROID_HOME", os.path.expanduser("~/Library/Android/sdk"))
    for subdir in ["platform-tools", "tools", "build-tools"]:
        sdk_path = os.path.join(android_home, subdir)
        if os.path.isdir(sdk_path):
            os.environ["PATH"] += os.pathsep + sdk_path
        elif subdir == "build-tools":
            # build-tools has versioned subdirectory
            build_tools_dir = sdk_path
            if os.path.isdir(build_tools_dir):
                for d in sorted(os.listdir(build_tools_dir), reverse=True):
                    bt_path = os.path.join(build_tools_dir, d)
                    if os.path.isdir(bt_path):
                        os.environ["PATH"] += os.pathsep + bt_path
                        break

    cmd = f"PYTHONPATH=scripts:$PYTHONPATH \"{sys.executable}\" scripts/task_executor.py " \
          f"--app \"{app}\" --root_dir \"{root_dir}\" " \
          f"--app_description \"{app_desc}\" --task \"{task}\""
    print_with_color(f"Running: {cmd}", "blue")
    os.system(cmd)
