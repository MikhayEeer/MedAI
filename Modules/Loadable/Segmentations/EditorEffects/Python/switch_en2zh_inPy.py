import os
import json
import re

def find_strings_in_python_files(directory, search_pattern, output_file):
    results = []

    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    line_number = 1
                    column_number = 1
                    for match in re.finditer(search_pattern, content, re.MULTILINE):
                        matched_string = match.group(1)
                        start_position = match.start()
                        end_position = match.end()

                        line_start = content.rfind('\n', 0, start_position)
                        line_number = line_start == -1 and 1 or content.count('\n', 0, line_start) + 2
                        column_number = start_position - line_start

                        position_info = {
                            "string": matched_string,
                            "file": file,
                            "line": line_number,
                            "column": column_number,
                            "翻译": ""
                        }
                        results.append(position_info)

                        column_number += len(matched_string) + 2

                        if content[start_position:end_position].endswith('\n'):
                            line_number += 1
                            column_number = 1

    write_mode = 'w'
    if os.path.exists(output_file):
        x = input("The output file already exists. Do you want to overwrite it? (y/n): ")
        if x.lower() == 'y':
            print("Overwriting the output file.")
        else:
            print("Not overwriting the output file.")
            write_mode = 'a'

    with open(output_file, write_mode, encoding='utf-8') as json_file:
        json.dump(results, json_file, indent=4, ensure_ascii=False)

if __name__ == '__main__':
    pwd = os.getcwd()
    print(f"The current working directory is: {pwd}")

    relative_path ="Modules\Loadable\Segmentations\EditorEffects\Python"
    switch_directory = 'SegmentEditorEffects'
    output_file = 'editoreffects_translate_strings.json'

    output_file = os.path.join(pwd, relative_path, output_file)
    switch_directory = os.path.join(pwd, relative_path, switch_directory)

    print(f"The output file is: {output_file}")
    print(f"The switch directory is: {switch_directory}")

    search_pattern = r'_\(["\']([^"\']+?)["\']\)'

    find_strings_in_python_files(switch_directory, search_pattern, output_file)