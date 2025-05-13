import re

# Read the main.py file
with open('main.py', 'r') as file:
    content = file.read()

# Find and remove all redundant navigation messages
pattern = r'# Add the main keyboard buttons reminder\s+send_response\(\s+chat_id,\s+"👇 \*One-Tap Navigation\* 👇\\n\\n"\s+"These persistent buttons make moving through the app effortless!",\s+parse_mode="Markdown",\s+reply_markup=MAIN_KEYBOARD\s+\)'

# Replace with a comment
replacement = "# No need to send additional messages about the keyboard"

# Perform the replacement
modified_content = re.sub(pattern, replacement, content)

# Write the modified content back to main.py
with open('main.py', 'w') as file:
    file.write(modified_content)

print("Navigation message fixes applied to main.py")
