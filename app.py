from flask import Flask, request, render_template, redirect, url_for, send_from_directory
import os

   app = Flask(__name__)
   app.config['UPLOAD_FOLDER'] = 'uploads'
   os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

   # Function definitions for parse_traces, parse_trace, merge_consecutive_recursions,
   # build_tree, escape_html, truncate_function_name, and create_html_tree go here
import re
from collections import defaultdict
from IPython.display import display, HTML

class Node:
    def __init__(self, call):
        self.call = call
        self.children = defaultdict(Node)
        self.parent = None
        self.count = 0

    def add_child(self, child_call):
        if child_call not in self.children:
            child_node = Node(child_call)
            child_node.parent = self
            self.children[child_call] = child_node
        return self.children[child_call]

def parse_traces(log_content):
    """Parse the log file content and return a list of stack traces."""
    traces = []
    current_trace = []
    for line in log_content.split('\n'):
        if line.startswith('#'):
            current_trace.append(line)
        elif current_trace:
            traces.append(list(reversed(current_trace)))
            current_trace = []
    if current_trace:
        traces.append(list(reversed(current_trace)))
    return traces

def parse_trace(trace):
    """Parse a single stack trace and return a list of function calls with their arguments."""
    calls = []
    for line in trace:
        match = re.match(r'#\d+\s+0x[0-9a-fA-F]+\s+in\s+(\w+(?:::?\w+)*)\s*(.*?)\s*$', line)
        if match:
            function_name = match.group(1)
            arguments = match.group(2).strip()
            if arguments:
                function_call = f"{function_name} {arguments}"
            else:
                function_call = f"{function_name} ()"
            calls.append(function_call)

    # Clean up function calls by removing everything after the first '()'
    cleaned_calls = []
    for call in calls:
        index = call.find('()')
        if index != -1:
            call = call[:index+2]  # Retain up to and including the first ')'
        cleaned_calls.append(call)
    #print(cleaned_calls)
    return cleaned_calls

def merge_consecutive_recursions(calls):
    """Merge consecutive recursive function calls in a stack trace."""
    if not calls:
        return []
    merged_calls = []
    prev_call = None
    for call in calls:
        if call != prev_call:
            merged_calls.append(call)
        prev_call = call
    return merged_calls

def build_tree(traces):
    """Build a call tree from the stack traces."""
    root = Node("main ()")  # assuming main will always be the root node, can be changed if more root nodes

    for trace in traces:
        calls = parse_trace(trace)
        if not calls:
            continue
        calls = merge_consecutive_recursions(calls)
        current_node = root
        current_node.count += 1
        for call in calls[1:]:
            current_node = current_node.add_child(call)
            current_node.count += 1

    return root

def escape_html(text):
    """Escape special HTML characters."""
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&#39;')

def truncate_function_name(name, max_length=70):
    """Truncate long function names and add ellipsis."""
    if len(name) > max_length:
        return name[:max_length] + '...'
    return name

def create_html_tree(root):
    """Create an HTML representation of the call tree."""
    total_traces = root.count
    total_running_time = total_traces * 10

    def node_to_html(node):
        percentage = (node.count / total_traces) * 100
        full_name = escape_html(node.call)
        truncated_name = truncate_function_name(full_name)
        label = f'<span class="function-label" title="{full_name}" style="color: red;">{truncated_name}</span> ({percentage:.2f}%)'
        if not node.children:
            return f'<li data-percentage="{percentage}">{label}</li>'
        else:
            sorted_children = sorted(node.children.values(), key=lambda n: n.count, reverse=True)
            children_html = ''.join(node_to_html(child) for child in sorted_children)
            return f'<li data-percentage="{percentage}"><span class="caret"><span class="function-label" title="{full_name}">{label}</span></span><ul class="nested">{children_html}</ul></li>'

    tree_html = node_to_html(root)
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
    <style>
    .nested {{
      display: none;
      padding-left: 20px;
      position: relative;
    }}
    .active {{
      display: block;
    }}
    .caret {{
      cursor: pointer;
      user-select: none;
      position: relative;
      display: flex;
      align-items: center;
    }}
    .caret::before {{
      content: "\\25B6";
      color: black;
      display: inline-block;
      margin-right: 6px;
    }}
    .caret-down::before {{
      transform: rotate(90deg);
    }}
    .function-label {{
      display: inline-block;
      white-space: nowrap;
      padding-left: 5px; /* Ensures text does not overlap with the vertical line */
    }}
    .nested::before {{
      content: "";
      position: absolute;
      left: -20px; /* Ensures the vertical line is correctly aligned */
      top: 0;
      bottom: 0;
      border-left: 2px solid #ccc;
    }}
    </style>
    </head>
    <body>

    <div style="margin-bottom: 20px; text-align: center;">
        <strong>Number of samples: {total_traces}</strong><br>
        <strong>Total running time: {total_running_time} seconds</strong><br><br>
        <label for="threshold">Threshold percentage:</label>
        <input type="number" id="threshold" placeholder="Enter threshold percentage" min="0" max="100" style="margin-right: 10px;">
        <button onclick="filterTree()">Apply</button>
    </div>

    <ul id="tree" style="list-style-type: none; padding-left: 0;">
      {tree_html}
    </ul>

    <script>
    document.addEventListener('DOMContentLoaded', function() {{
        const toggler = document.getElementsByClassName("caret");
        for (let i = 0; i < toggler.length; i++) {{
            toggler[i].addEventListener("click", function() {{
                this.parentElement.querySelector(".nested").classList.toggle("active");
                this.classList.toggle("caret-down");
            }});
        }}
    }});

    function filterTree() {{
        const threshold = parseFloat(document.getElementById('threshold').value);
        const nodes = document.querySelectorAll('li[data-percentage]');
        nodes.forEach(node => {{
            const percentage = parseFloat(node.getAttribute('data-percentage'));
            if (percentage < threshold) {{
                node.style.display = 'none';
            }} else {{
                node.style.display = 'block';
            }}
        }});
    }}
    </script>

    </body>
    </html>
    '''

if __name__ == '__main__':
    with open('postproc.log', 'r') as f:
        log_content = f.read()
    traces = parse_traces(log_content)
    root = build_tree(traces)
    html_content = create_html_tree(root)

    # Write the HTML content to a file
    with open('/content/result.html', 'w') as f:
        f.write(html_content)

    # Display the HTML content in the notebook
    #display(HTML(html_content))


   @app.route('/')
   def index():
       return render_template('index.html')

   @app.route('/upload', methods=['POST'])
   def upload_file():
       if 'file' not in request.files:
           return redirect(request.url)
       file = request.files['file']
       if file.filename == '':
           return redirect(request.url)
       if file:
           filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
           file.save(filepath)
           with open(filepath, 'r') as f:
               log_content = f.read()
           traces = parse_traces(log_content)
           root = build_tree(traces)
           html_content = create_html_tree(root)
           output_filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'result.html')
           with open(output_filepath, 'w') as f:
               f.write(html_content)
           return redirect(url_for('view_result', filename='result.html'))

   @app.route('/uploads/<filename>')
   def view_result(filename):
       return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

   if __name__ == '__main__':
       app.run(debug=True)