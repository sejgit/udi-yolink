import os

replacements = {
    "I_TEMP_DEG": "ITEMPDEG",
    "I_TEMP_F": "ITEMPF",
    "I_CLISPH_DEG": "ICLISPHDEG",
    "I_CLISPH_F": "ICLISPHF",
    "I_CLISPC_DEG": "ICLISPCDEG",
    "I_CLISPC_F": "ICLISPCF",
    "I_TSTAT_MODE": "ITSTATMODE",
    "I_TSTAT_FAN": "ITSTATFAN",
    "I_CLISMD_DEG": "ICLISMDDEG",
    "I_TSTAT_HCS": "ITSTATHCS",
    "I_HUMIDITY": "IHUMIDITY",
    "I_AUX_HEAT": "IAUXHEAT",
    "I_STAGE2": "ISTAGE2",
    "I_ECO_MODE": "IECOMODE",
    "I_DR_RUNNING": "IDRRUNNING",
    "I_MINRUNTIME": "IMINRUNTIME",
    "I_MUTE": "IMUTE",
    "I_MENULOCK": "IMENULOCK",
    "I_HOURS": "IHOURS",
    "I_MASTER_SRC": "IMASTERSRC",
    "I_SUSPENDED_ST": "ISUSPENDEDST",
    "I_ONLINE_ST": "IONLINEST"
}

files = [
    r"profile/nodedef/nodedefs.xml",
    r"profile/editor/editors.xml"
]

for file_path in files:
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        continue
        
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    new_content = content
    for old, new in replacements.items():
        new_content = new_content.replace(f'"{old}"', f'"{new}"') # replace editor="I_..."
        new_content = new_content.replace(f'id="{old}"', f'id="{new}"') # replace id="I_..."
        # Just to be safe, exact string replacement might be safer if they appear elsewhere but surrounded by quotes is key for XML attributes.
        # However, editor="I_TEMP_DEG" and id="I_TEMP_DEG" cover most cases.
        # Wait, if I replace just the string, I might replace substrings. But these are all upper case with I_. 
        # Using string replacement directly on the content is safer if we are sure there are no partial matches.
        # Given the names, they seem unique enough.
        
    # Let's do a direct replace of the strings themselves to cover all cases (like init="GV1" which is not relevant here but just in case referenced differently)
    # Actually, verify that we don't partial match.
    # I_TEMP_DEG is not a substring of I_TEMP_DEG_2 (if it existed). 
    # But I_TEMP is not in the list.
    
    for old, new in replacements.items():
        new_content = new_content.replace(old, new)

    if content != new_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Updated {file_path}")
    else:
        print(f"No changes in {file_path}")
