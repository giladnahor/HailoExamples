#!/usr/bin/env python3
import re

def reformat_pipeline(pipeline, line_limit=80):
    # Remove multiple spaces and tabs
    formatted_pipeline = re.sub(r'\s+', ' ', pipeline)

    # Check for multiple consecutive exclamation marks
    if re.search(r'! +!', formatted_pipeline):
        raise ValueError("Error: Multiple consecutive '!' found in the pipeline.")

    # Break into multiple lines if too long
    broken_lines = []
    while len(formatted_pipeline) > 0:
        if len(formatted_pipeline) <= line_limit:
            broken_lines.append(formatted_pipeline)
            break

        # Find the last occurrence of '!' before or after the line_limit
        break_index = formatted_pipeline.find('!', line_limit)
        if break_index == -1:
            # If '!' is not found, take the rest of the string
            break_index = len(formatted_pipeline) - 1

        # Split the line at the break_index and add a backslash
        broken_lines.append(formatted_pipeline[:break_index + 1].rstrip() + " \\")
        formatted_pipeline = formatted_pipeline[break_index + 1:].lstrip()

    return '\n'.join(broken_lines)

# Input the pipeline as a string
input_pipeline = input("Enter your GStreamer pipeline: ")

try:
    formatted_pipeline = reformat_pipeline(input_pipeline)
    print("\nFormatted Pipeline:")
    print(formatted_pipeline)
except ValueError as e:
    print(e)
