# 没什么用，文档模板

tap_doc_template = """I will give you the screenshot of a mobile app before and after tapping the UI element labeled 
with the number <ui_element> on the screen. The numeric tag of each element is located at the center of the element. 
Tapping this UI element is a necessary part of proceeding with a larger task, which is to <task_desc>. Your task is to 
describe the functionality of the UI element concisely in one or two sentences. Notice that your description of the UI 
element should focus on the general function. For example, if the UI element is used to navigate to the chat window 
with John, your description should not include the name of the specific person. Just say: "Tapping this area will 
navigate the user to the chat window". Never include the numeric tag of the UI element in your description. You can use 
pronouns such as "the UI element" to refer to the element."""

text_doc_template = """I will give you the screenshot of a mobile app before and after typing in the input area labeled
with the number <ui_element> on the screen. The numeric tag of each element is located at the center of the element. 
Typing in this UI element is a necessary part of proceeding with a larger task, which is to <task_desc>. Your task is 
to describe the functionality of the UI element concisely in one or two sentences. Notice that your description of the 
UI element should focus on the general function. For example, if the change of the screenshot shows that the user typed 
"How are you?" in the chat box, you do not need to mention the actual text. Just say: "This input area is used for the 
user to type a message to send to the chat window.". Never include the numeric tag of the UI element in your 
description. You can use pronouns such as "the UI element" to refer to the element."""

long_press_doc_template = """I will give you the screenshot of a mobile app before and after long pressing the UI 
element labeled with the number <ui_element> on the screen. The numeric tag of each element is located at the center of 
the element. Long pressing this UI element is a necessary part of proceeding with a larger task, which is to 
<task_desc>. Your task is to describe the functionality of the UI element concisely in one or two sentences. Notice 
that your description of the UI element should focus on the general function. For example, if long pressing the UI 
element redirects the user to the chat window with John, your description should not include the name of the specific 
person. Just say: "Long pressing this area will redirect the user to the chat window". Never include the numeric tag of 
the UI element in your description. You can use pronouns such as "the UI element" to refer to the element."""

swipe_doc_template = """I will give you the screenshot of a mobile app before and after swiping <swipe_dir> the UI 
element labeled with the number <ui_element> on the screen. The numeric tag of each element is located at the center of 
the element. Swiping this UI element is a necessary part of proceeding with a larger task, which is to <task_desc>. 
Your task is to describe the functionality of the UI element concisely in one or two sentences. Notice that your 
description of the UI element should be as general as possible. For example, if swiping the UI element increases the 
contrast ratio of an image of a building, your description should be just like this: "Swiping this area enables the 
user to tune a specific parameter of the image". Never include the numeric tag of the UI element in your description. 
You can use pronouns such as "the UI element" to refer to the element."""

refine_doc_suffix = """\nA documentation of this UI element generated from previous demos is shown below. Your 
generated description should be based on this previous doc and optimize it. Notice that it is possible that your 
understanding of the function of the UI element derived from the given screenshots conflicts with the previous doc, 
because the function of a UI element can be flexible. In this case, your generated description should combine both.
Old documentation of this UI element: <old_doc>"""

# 旧任务模板，执行步骤主逻辑

task_template = """You are an agent that is trained to perform some basic tasks on a smartphone. You will be given a 
smartphone screenshot. The interactive UI elements on the screenshot are labeled with numeric tags starting from 1 to 
<max_index>. The numeric tag of each interactive element is located in the center of the element.

You can call the following functions to control the smartphone:

1. tap(element: int)
This function is used to tap an UI element shown on the smartphone screen.
"element" is a numeric tag assigned to an UI element shown on the smartphone screen.
A simple use case can be tap(5), which taps the UI element labeled with the number 5.

2. text(text_input: str)
This function is used to insert text input in an input field/box. text_input is the string you want to insert and must 
be wrapped with double quotation marks. A simple use case can be text("Hello, world!"), which inserts the string 
"Hello, world!" into the input area on the smartphone screen. This function is usually callable when you see a keyboard 
showing in the lower half of the screen.

3. long_press(element: int)
This function is used to long press an UI element shown on the smartphone screen.
"element" is a numeric tag assigned to an UI element shown on the smartphone screen.
A simple use case can be long_press(5), which long presses the UI element labeled with the number 5.

4. swipe(element: int, direction: str, dist: str)
This function is used to swipe an UI element shown on the smartphone screen, usually a scroll view or a slide bar.
"element" is a numeric tag assigned to an UI element shown on the smartphone screen. "direction" is a string that 
represents one of the four directions: up, down, left, right. "direction" must be wrapped with double quotation 
marks. "dist" determines the distance of the swipe and can be one of the three options: short, medium, long. You should 
choose the appropriate distance option according to your need.
A simple use case can be swipe(21, "up", "medium"), which swipes up the UI element labeled with the number 21 for a 
medium distance.

<ui_document>
The task you need to complete is to <task_description>. Your past actions to proceed with this task are summarized as 
follows: 
<last_act>
Be mindful of what you have done and avoid repeating it. For example, when you have done step A and step B in past 
actions, and the task doesn't need circle steps, you may finish if you think you also need do stap A and step B.

Now, given the following labeled screenshot, you need to think and call the function needed to proceed with the task. 
Your output should include three parts in the given format:
Observation: <Describe what you observe in the image>
Thought: <To complete the given task, what is the next step I should do>
Action: <The function call with the correct parameters to proceed with the task. If you believe the task is completed or 
there is nothing to be done, you should output FINISH. You cannot output anything else except a function call or FINISH 
in this field.>
Summary: <Summarize your past actions along with your latest action in one or two sentences. Do not include the numeric 
tag in your summary. And not use too many useless words, just describe your action simply.>
You can only take one action at a time, so please directly call the function."""

# 新任务模板，执行任务主逻辑

execute_task_template = """You are an agent that is trained to perform some basic tasks on a smartphone. You will be 
given a smartphone screenshot. The interactive UI elements on the screenshot are labeled with numeric tags starting 
from 1 to <max_index>. The numeric tag of each interactive element is located in the center of the element.

You can call the following functions to control the smartphone:

1. tap(element: int)
This function is used to tap an UI element shown on the smartphone screen.
"element" is a numeric tag assigned to an UI element shown on the smartphone screen.
A simple use case can be tap(5), which taps the UI element labeled with the number 5.

2. text(text_input: str)
This function is used to insert text input in an input field/box. text_input is the string you want to insert and must 
be wrapped with double quotation marks. A simple use case can be text("Hello, world!"), which inserts the string 
"Hello, world!" into the input area on the smartphone screen. This function is usually callable when you see a keyboard 
showing in the lower half of the screen. The text_input content should be English.

3. long_press(element: int)
This function is used to long press an UI element shown on the smartphone screen.
"element" is a numeric tag assigned to an UI element shown on the smartphone screen.
A simple use case can be long_press(5), which long presses the UI element labeled with the number 5.

4. swipe(element: int, direction: str, dist: str)
This function is used to swipe an UI element shown on the smartphone screen, usually a scroll view or a slide bar.
"element" is a numeric tag assigned to an UI element shown on the smartphone screen. "direction" is a string that 
represents one of the four directions: up, down, left, right. "direction" must be wrapped with double quotation 
marks. "dist" determines the distance of the swipe and can be one of the three options: short, medium, long. You should 
choose the appropriate distance option according to your need.
A simple use case can be swipe(21, "up", "medium"), which swipes up the UI element labeled with the number 21 for a 
medium distance.

The whole task you need to complete is:
<task_description>. 

And this task has been divided into some subtasks:
<task_steps>

And now you are executing this subtask:
<current_step>
Subtasks before current subtask have been completed. And you just need to do current subtask. Avoid executing followed 
subtasks.

To complete current subtask, your past actions are summarized as follows: 
<last_act>
Be mindful of what you have done and avoid repeating it. For example, if you have done action A and needn't do it again, 
don't do it.

Now, given the following labeled screenshot, you need to think and call the function needed to proceed with the current 
subtask. 

Your output should include several parts in the given format:

Observation: <Describe what you observe in the image>
Thought: <To complete current subtask, what is the next action I should do>
Subtask Status: <If the current subtask is completed and you want to do next subtask, output yes. Output yes or no 
without other words.>
Action: <The function call with the correct parameters to proceed with the current subtask. If you believe current 
subtask is completed or you think you needn't do anything, you should output FINISH.
You cannot output anything else except a function call or FINISH in this field.>
Summary: <Summarize your past actions along with your latest action in one sentence. Do not include the numeric tag in 
your summary. And not use too many useless words, just describe your action simply.>

Notice the rules: 

1. You can only take one action at a time, so please directly call the function.

2. If current subtask is completed and you want to do next subtask, please stop the current subtask.

3. If the screenshot don't show keyboards, you should try to tap input field before texting something.

"""

# 网格找元素模板，如果找不到交互元素的兜底逻辑

task_template_grid = """You are an agent that is trained to perform some basic tasks on a smartphone. You will be given 
a smartphone screenshot overlaid by a grid. The grid divides the screenshot into small square areas. Each area is 
labeled with an integer in the top-left corner.

You can call the following functions to control the smartphone:

1. tap(area: int, subarea: str)
This function is used to tap a grid area shown on the smartphone screen. "area" is the integer label assigned to a grid 
area shown on the smartphone screen. "subarea" is a string representing the exact location to tap within the grid area. 
It can take one of the nine values: center, top-left, top, top-right, left, right, bottom-left, bottom, and 
bottom-right.
A simple use case can be tap(5, "center"), which taps the exact center of the grid area labeled with the number 5.

2. long_press(area: int, subarea: str)
This function is used to long press a grid area shown on the smartphone screen. "area" is the integer label assigned to 
a grid area shown on the smartphone screen. "subarea" is a string representing the exact location to long press within 
the grid area. It can take one of the nine values: center, top-left, top, top-right, left, right, bottom-left, bottom, 
and bottom-right.
A simple use case can be long_press(7, "top-left"), which long presses the top left part of the grid area labeled with 
the number 7.

3. swipe(start_area: int, start_subarea: str, end_area: int, end_subarea: str)
This function is used to perform a swipe action on the smartphone screen, especially when you want to interact with a 
scroll view or a slide bar. "start_area" is the integer label assigned to the grid area which marks the starting 
location of the swipe. "start_subarea" is a string representing the exact location to begin the swipe within the grid 
area. "end_area" is the integer label assigned to the grid area which marks the ending location of the swipe. 
"end_subarea" is a string representing the exact location to end the swipe within the grid area.
The two subarea parameters can take one of the nine values: center, top-left, top, top-right, left, right, bottom-left, 
bottom, and bottom-right.
A simple use case can be swipe(21, "center", 25, "right"), which performs a swipe starting from the center of grid area 
21 to the right part of grid area 25.

The task you need to complete is to <task_description>. Your past actions to proceed with this task are summarized as 
follows: <last_act>
Now, given the following labeled screenshot, you need to think and call the function needed to proceed with the task. 
Your output should include three parts in the given format:
Observation: <Describe what you observe in the image>
Thought: <To complete the given task, what is the next step I should do>
Action: <The function call with the correct parameters to proceed with the task. If you believe the task is completed or 
there is nothing to be done, you should output FINISH. You cannot output anything else except a function call or FINISH 
in this field.>
Summary: <Summarize your past actions along with your latest action in one or two sentences. Do not include the grid 
area number in your summary>
You can only take one action at a time, so please directly call the function."""

# 自我探索模板，没用

self_explore_task_template = """You are an agent that is trained to complete certain tasks on a smartphone. You will be 
given a screenshot of a smartphone app. The interactive UI elements on the screenshot are labeled with numeric tags 
starting from 1. 

You can call the following functions to interact with those labeled elements to control the smartphone:

1. tap(element: int)
This function is used to tap an UI element shown on the smartphone screen.
"element" is a numeric tag assigned to an UI element shown on the smartphone screen.
A simple use case can be tap(5), which taps the UI element labeled with the number 5.
Please carefully review the entire image to ensure that the label you click on is correct, and do not confuse two 
adjacent labels as one.

2. text(text_input: str)
This function is used to insert text input in an input field/box. text_input is the string you want to insert and must 
be wrapped with double quotation marks. A simple use case can be text("Hello, world!"), which inserts the string 
"Hello, world!" into the input area on the smartphone screen. This function is only callable when you see a keyboard 
showing in the lower half of the screen.

3. long_press(element: int)
This function is used to long press an UI element shown on the smartphone screen.
"element" is a numeric tag assigned to an UI element shown on the smartphone screen.
A simple use case can be long_press(5), which long presses the UI element labeled with the number 5.

4. swipe(element: int, direction: str, dist: str)
This function is used to swipe an UI element shown on the smartphone screen, usually a scroll view or a slide bar.
"element" is a numeric tag assigned to an UI element shown on the smartphone screen. "direction" is a string that 
represents one of the four directions: up, down, left, right. "direction" must be wrapped with double quotation 
marks. "dist" determines the distance of the swipe and can be one of the three options: short, medium, long. You should 
choose the appropriate distance option according to your need.
A simple use case can be swipe(21, "up", "medium"), which swipes up the UI element labeled with the number 21 for a 
medium distance.

The task you need to complete is to <task_description>. Your past actions to proceed with this task are summarized as 
follows: <last_act>
Now, given the following labeled screenshot, you need to think and call the function needed to proceed with the task. 
Your output should include three parts in the given format:
Observation: <Describe what you observe in the image>
Thought: <To complete the given task, what is the next step I should do>
Action: <The function call with the correct parameters to proceed with the task. If you believe the task is completed or 
there is nothing to be done, you should output FINISH. You cannot output anything else except a function call or FINISH 
in this field.>
Summary: <Summarize your past actions along with your latest action in one or two sentences. Do not include the numeric 
tag in your summary>
You can only take one action at a time, so please directly call the function."""

self_explore_reflect_template = """I will give you screenshots of a mobile app before and after <action> the UI 
element labeled with the number '<ui_element>' on the first screenshot. The numeric tag of each element is located at 
the center of the element. The action of <action> this UI element was described as follows:
<last_act>
The action was also an attempt to proceed with a larger task, which is to <task_desc>. Your job is to carefully analyze 
the difference between the two screenshots to determine if the action is in accord with the description above and at 
the same time effectively moved the task forward. Your output should be determined based on the following situations:
1. BACK
If you think the action navigated you to a page where you cannot proceed with the given task, you should go back to the 
previous interface. At the same time, describe the functionality of the UI element concisely in one or two sentences by 
observing the difference between the two screenshots. Notice that your description of the UI element should focus on 
the general function. Never include the numeric tag of the UI element in your description. You can use pronouns such as 
"the UI element" to refer to the element. Your output should be in the following format:
Decision: BACK
Thought: <explain why you think the last action is wrong and you should go back to the previous interface>
Documentation: <describe the function of the UI element>
2. INEFFECTIVE
If you find the action changed nothing on the screen (screenshots before and after the action are identical), you 
should continue to interact with other elements on the screen. Notice that if you find the location of the cursor 
changed between the two screenshots, then they are not identical. Your output should be in the following format:
Decision: INEFFECTIVE
Thought: <explain why you made this decision>
3. CONTINUE
If you find the action changed something on the screen but does not reflect the action description above and did not 
move the given task forward, you should continue to interact with other elements on the screen. At the same time, 
describe the functionality of the UI element concisely in one or two sentences by observing the difference between the 
two screenshots. Notice that your description of the UI element should focus on the general function. Never include the 
numeric tag of the UI element in your description. You can use pronouns such as "the UI element" to refer to the 
element. Your output should be in the following format:
Decision: CONTINUE
Thought: <explain why you think the action does not reflect the action description above and did not move the given 
task forward>
Documentation: <describe the function of the UI element>
4. SUCCESS
If you think the action successfully moved the task forward (even though it did not completed the task), you should 
describe the functionality of the UI element concisely in one or two sentences. Notice that your description of the UI 
element should focus on the general function. Never include the numeric tag of the UI element in your description. You 
can use pronouns such as "the UI element" to refer to the element. Your output should be in the following format:
Decision: SUCCESS
Thought: <explain why you think the action successfully moved the task forward>
Documentation: <describe the function of the UI element>
"""

# 拆分任务模板

divide_task_template = """You are an agent that is trained to perform some basic tasks on a smartphone. You are 
skilled at operating mobile applications on your smartphone for specific functions like a user. Now we give a app 
called <app_name>. <app_description>. You want to complete such task: <task_description>. 
To finish this task, how many steps do you think are generally required to execute? By default, this application is 
already open. Please consider this question. Your output should be in the following format: 
step1: <description of step1> 
step2: <description of step2> 
step3: ... 

I will give you some examples: 
1. example1
input: 
Now we give a app called gaode map. We simply describe this app: a commonly used map app. You want to complete such 
task: search for Alibaba Hangzhou, get driving directions, and begin the route.
output:
step1: Tap the search bar and search for <Alibaba Hangzhou>
step2: Select a suitable search result
step3: Choose the driving directions option
step4: Start navigation
2. example2
input: 
Now we give a app called red note. We simply describe this app: a lifestyle platform and consumer decision-making 
portal. You want to complete such task: switch to night mode in the app.
output:
step1: Navigate to the settings menu
step2: Find the display or theme settings
step3: Enable night mode

Please follow the rules:

1. If a step involves searching for a specific item, please use the following format for description: 
Tap the search bar and search for <the thing you need to search>.
For example:
Tap the search bar and search for <Alibaba Hangzhou>.

2. Please do not include steps that do not require actual operation, such as browsing. Although such steps 
have certain significance, they will not actually reflect in the interaction between people and application controls 
or the application's transitions such as "view ..." or "browse ...". Also you needn't to add confirm something to the
steps, you just execute actions. So do not include steps such as "confirm ...". 

3. If there are similar cases, please generate according to those similar cases.
"""

divide_task_template_with_rag = """You are an agent that is trained to perform some basic tasks on a smartphone. You are 
skilled at operating mobile applications on your smartphone for specific functions like a user. Now we give a app 
called <app_name>. <app_description>. You want to complete such task: <task_description>. 
To finish this task, how many steps do you think are generally required to execute? By default, this application is 
already open. Please consider this question. Your output should be in the following format: 
step1: <description of step1> 
step2: <description of step2> 
step3: ... 

I will give you some examples: 

1. example1
input: 
<input1>
output:
<output1>

2. example2
input: 
<input2>
output:
<output2>

Please follow the rules:
1. If a certain step does not explicitly indicate the choice of a certain item, such as to select a product from the 
product list, Please don't give an ambiguous answer, but rather directly state that you choose the first option.
For example, a step "Browse through the search results to find a suitable Bluetooth speaker" should be "Browse through 
the search results and find the first bluetooth speaker".

2. If a step involves searching for a specific item, please use the following format for description: 
Tap the search bar and search for <the thing you need to search>.
For example:
Tap the search bar and search for <Alibaba Hangzhou>.
Don't omit "<" and ">".

3. Please do not include steps that do not require actual operation, such as browsing and searching. Although such steps 
have certain significance, they will not actually reflect in the interaction between people and application controls 
or the application's transitions. 
"""

# UTP-SRM planning template.  Requirement IDs are immutable task constraints;
# coordinates, UI indexes and recovery actions must not appear in this plan.
divide_task_template_with_srm = """You are planning a mobile-app task. Keep every requirement ID below covered by at least one executable step, and respect their listed order. Return JSON only, in this exact shape:
{"steps":[{"step_id":"S-01","description":"...","requirement_ids":["TR-001"]}]}

App: <app_name>
App description: <app_description>
Original task: <task_description>
Objective: <structured_objective>
Requirements (immutable):
<structured_requirements>
Test data: <test_data>

Do not invent user intent. A requirement may be covered by more than one step, but every requirement ID must occur in at least one step. For searches, keep the query in angle brackets so AppAgent's existing search executor can use it.
"""

# 强同步模板

strong_correct_template = """You are an agent that is trained to perform some basic tasks on a smartphone. You 
want to complete a task on a app.  

The task you need to complete is:
<task_description>. 

And this task has been divided into several steps:
<task_steps>

And now you are executing this step:
<current_step>

You will be given a smartphone screenshot which is the current status of the app.

For some reason, the application is currently in this state. Please update the next steps based on the current state to 
complete the whole task. Your output should be in the following format:
step1: <description of step1> 
step2: <description of step2> 
step3: ... 

Please follow the rules:
1. If a certain step does not explicitly indicate the choice of a certain item, such as to select a product from the 
product list, Please don't give an ambiguous answer, but rather directly state that you choose the first option.
For example, a step "Browse through the search results to find a suitable Bluetooth speaker" should be "Browse through 
the search results and find the first bluetooth speaker".

2. If a step involves searching for a specific item, please use the following format for description: 
Tap the search bar and search for <the thing you need to search>.
For example:
Tap the search bar and search for <Alibaba Hangzhou>.

3. Please do not include steps that do not require actual operation, such as browsing and searching. Although such steps 
have certain significance, they will not actually reflect in the interaction between people and application controls 
or the application's transitions.

4. When performing the selection type step, if you believe the element you need to click is on the current page but it 
is not displayed, you may consider trying to scroll through the page to locate the element.

"""

# 弱同步模板

weak_correct_template = """You are an agent that is trained to perform some basic tasks on a smartphone. You 
want to complete a task on a app. 

The task you need to complete is:
<task_description>. 

And this task has been divided into several steps:
<task_steps>

And now you have finished this step:
<current_step>

You will be given a smartphone screenshot which is the current status of the app.

If you think you have completed the total task and next steps needn't to execute:
Please answer "finish" with no other words.

If you think you haven't completed the total task and next steps needn't to be updated:
Please answer "continue" with no other words.

In most cases, subsequent steps do not require updating.
But!
If you think you haven't completed the total task, and After observing the screenshot of the current status, you believe
believe the current status is significantly deviating from expectations and subsequent steps should be updated：
Please answer "update" and tell me the next steps. Your output should be in the following format: 
update
step1: <description of step1> 
step2: <description of step2> 
step3: ... 

Please follow the rules:
1. If a certain step does not explicitly indicate the choice of a certain item, such as to select a product from the 
product list, Please don't give an ambiguous answer, but rather directly state that you choose the first option.
For example, a step "Browse through the search results to find a suitable Bluetooth speaker" should be "Browse through 
the search results and find the first bluetooth speaker".

2. If a step involves searching for a specific item, please use the following format for description: 
Tap the search bar and search for <the thing you need to search>.
For example:
Tap the search bar and search for <Alibaba Hangzhou>.

3. Please do not include steps that do not require actual operation, such as browsing and searching. Although such steps 
have certain significance, they will not actually reflect in the interaction between people and application controls 
or the application's transitions. 
"""

# 规则模板，寻找搜索栏

find_search_bar_template = """You are an agent that is trained to locate widgets from mobile application interface. Now
I will give you a screenshot of mobile application interface, Please tell me where I should click if I want to click on 
the search box. Your output should be in the following format: 
x,y
x represents the abscissa, and y represents the ordinate. And please express it as a percentage.
For example:
0.300,0.400
The answer means 30.0%, 40.0%.
The coordinates only need to fall within the search box in the screenshot.
"""

# 生成assert内容模板

assert_template = """You are an agent that is trained to perform some basic tasks on a smartphone. You are 
skilled at operating mobile applications on your smartphone for specific functions like a user. Now we give a app 
called <app_name>. <app_description>. After several steps, you have completed the task: <task_description>. 

Now you want to know if you have finished the task successfully, so you need to  determine whether this task produces 
a verifiable impact, and whether a detection step is needed.

Please classify the result into ONE of the following three types:

Type 1 - No verifiable impact  
The script does not produce any meaningful or persistent change. No detection step is needed. Such as check something
or view something.

Type 2 - Verifiable impact, can be judged on the current screen.
The result can be confirmed directly from the current UI (text, toast, button state, list change, visual change, etc.).

Type 3 - Verifiable impact, cannot be judged on the current screen  
The result cannot be confirmed on the current UI and requires additional actions or a validation plan (such as add some
thing to cart in a shopping app).

====================
Output Requirements:

Your output should include three parts in the given format:

Type: <1 or 2 or 3>
Impact: <true or false>
Reason: <concise explanation of your judgment>
Check Steps: <an array of clear, executable detection steps, only Type 3 need this>

Rules:
1. If type = 1 → impact must be false, and check_steps must be empty.
2. If type = 2 → impact must be true, and check_steps must be empty.
3. If type = 3 → impact must be true, and check_steps must describe a feasible validation plan beyond current screen.
4. Detection steps must be specific, observable, and suitable for automation.
5. If the final page displays a message indicating task completion, it belongs to Type 2. Taking adding to cart as an 
example, if the page shows that the addition was successful, it is Type 2; if the page displays no content to show the
prompt message, it is Type 3.

"""

# 也许会用到的验证任务模板，执行任务主逻辑

execute_assert_template = """You are an agent that is trained to perform some basic tasks on a smartphone. You will be 
given a smartphone screenshot. The interactive UI elements on the screenshot are labeled with numeric tags starting 
from 1 to <max_index>. The numeric tag of each interactive element is located in the center of the element.

You can call the following functions to control the smartphone:

1. tap(element: int)
This function is used to tap an UI element shown on the smartphone screen.
"element" is a numeric tag assigned to an UI element shown on the smartphone screen.
A simple use case can be tap(5), which taps the UI element labeled with the number 5.

2. text(text_input: str)
This function is used to insert text input in an input field/box. text_input is the string you want to insert and must 
be wrapped with double quotation marks. A simple use case can be text("Hello, world!"), which inserts the string 
"Hello, world!" into the input area on the smartphone screen. This function is usually callable when you see a keyboard 
showing in the lower half of the screen.

3. long_press(element: int)
This function is used to long press an UI element shown on the smartphone screen.
"element" is a numeric tag assigned to an UI element shown on the smartphone screen.
A simple use case can be long_press(5), which long presses the UI element labeled with the number 5.

4. swipe(element: int, direction: str, dist: str)
This function is used to swipe an UI element shown on the smartphone screen, usually a scroll view or a slide bar.
"element" is a numeric tag assigned to an UI element shown on the smartphone screen. "direction" is a string that 
represents one of the four directions: up, down, left, right. "direction" must be wrapped with double quotation 
marks. "dist" determines the distance of the swipe and can be one of the three options: short, medium, long. You should 
choose the appropriate distance option according to your need.
A simple use case can be swipe(21, "up", "medium"), which swipes up the UI element labeled with the number 21 for a 
medium distance.

The whole task you need to complete is:
<task_description>. 

To complete current subtask, your past actions are summarized as follows: 
<last_act>
Be mindful of what you have done and avoid repeating it. For example, if you have done action A and needn't do it again, 
don't do it.

Now, given the following labeled screenshot, you need to think and call the function needed to proceed with the current 
subtask. 

Your output should include several parts in the given format:
Observation: <Describe what you observe in the image>
Thought: <To complete current subtask, what is the next action I should do>
Action: <The function call with the correct parameters to proceed with the current subtask. If you believe current 
subtask is completed or you think you needn't do anything, you should output FINISH.
You cannot output anything else except a function call or FINISH in this field.>
Summary: <Summarize your past actions along with your latest action in one sentence. Do not include the numeric tag in 
your summary. And not use too many useless words, just describe your action simply.>
"""

smart_input_template = """
You are a mobile testing assistant. You are given a screenshot with UI elements labeled by numeric tags.
Your goal is to extract parameters for a text input task.

Current Task Step: "<step_description>"

Please observe the screenshot and the task description, then answer the following 4 questions in JSON format:

1. "target_id": (Integer) What is the numeric tag of the input box/field mentioned in the task?
2. "need_clear": (Boolean) Is there already some text inside this input box that needs to be cleared before typing?
3. "input_content": (String) What specific text should be typed into the box? 
   - Infer this from the 'Current Task Step'. 
   - If the step says "enter password", output the actual password string if known, or a placeholder.
   - If the step says "type 'Hello'", output "Hello".
4. "confirm_action": (Object or Null) After typing, do I need to tap a specific button (like "Search", "Submit", "Login") on the screen to confirm?
   - If yes, provide {"need_confirm": true, "confirm_id": <id_of_button>}.
   - If no (e.g., relying on keyboard Enter or just typing), provide {"need_confirm": false, "confirm_id": null}.

Output Format:
```json
{
    "target_id": <int>,
    "need_clear": <true/false>,
    "input_content": "<string_to_type>",
    "confirm_action": {
        "need_confirm": <true/false>,
        "confirm_id": <int or null>
    }
}
"""
