"""
Certain config files need to be filled with information which we can only know at runtime with the given arguments.
For this files we use the .template extension. This file defines a function that reads a specific file and replaces certain characters with other characters.
"""

def replaceInTemplateFile(file: str, replaceDict: dict) -> str:
    """
    Replaces all keys from replaceDict with their corresponding values inside the file. Returns the new file.
    The new file is stored at the same location but without the .template extension
    """
    with open(file, 'r') as f:
        content = f.read()
    
    for key, value in replaceDict.items():
        content = content.replace(key, value)
    
    newFile = file.replace(".template", '')
    
    with open(newFile, 'w') as f:
        f.write(content)

    return newFile