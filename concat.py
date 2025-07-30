import os

base_dir = r'C:/Users/lwhitaker/personal\SYSC4918\SYSC4918\src'
output_file = 'cocat.txt'


# Clear the output file before starting
with open(output_file, 'w', encoding='utf-8') as outfile:
    outfile.write('')

with open(output_file, 'a', encoding='utf-8') as outfile:
    for root, dirs, files in os.walk(base_dir):
        # Skip directories named "test" at any level
        dirs[:] = [d for d in dirs if d.lower() != 'test']
        for file in files:
            # Check for all required file extensions
            if file.endswith(('.py')):
                file_path = os.path.join(root, file)
                outfile.write(f'File: {file_path}\n')
                with open(file_path, 'r', encoding='utf-8') as infile:
                    outfile.write(infile.read())
                outfile.write('\n\n')

print(f'Concatenation complete. Output file: {output_file}')