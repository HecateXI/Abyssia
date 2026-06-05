import sys
import re
from pathlib import Path

path = Path(r"c:\Users\HomeAdmin\Downloads\bot\cogs\rpg_battle.py")
content = path.read_text(encoding="utf-8")

old_str = """        team_lines = []
        for cr in left_team:
            lvl = int(cr.get("level", 1))
            name = str(cr.get("name", "?"))
            w = cr.get("_weapon") if isinstance(cr.get("_weapon"), dict) else None
            w_name = str(w.get("name", "")) if w else None
            w_part = f" \u2022 **{w_name}** ({str(w.get('rarity', 'Common'))})" if w_name else ""
            team_lines.append(f"Lv.{lvl} {name}{w_part}")
        embed.add_field(name="🛡️ Your Team", value="\\n".join(team_lines), inline=True)
        enemy_lines = []
        for cr in right_team:
            lvl = int(cr.get("level", 1))
            name = str(cr.get("name", "?"))
            enemy_lines.append(f"Lv.{lvl} {name}")
        embed.add_field(name="👾 Enemy Team", value="\\n".join(enemy_lines), inline=True)
        embed.set_image(url="attachment://abyssia_battle.png")"""

# Note the unicode characters were escaped in python as \U0001f6e1\ufe0f but might be stored directly as 🛡️ and 👾.
# I will use a regex to replace everything between "embed.remove_footer()" and "if battle_message is not None:"

new_str = """        team_lines = []
        for cr in left_team:
            lvl = int(cr.get("level", 1))
            name = str(cr.get("name", "?"))
            w = cr.get("_weapon") if isinstance(cr.get("_weapon"), dict) else None
            w_name = str(w.get("name", "")) if w else None
            w_part = f" \u2022 **{w_name}**" if w_name else ""
            team_lines.append(f"Lv.{lvl} {name}{w_part}")
            
        enemy_lines = []
        for cr in right_team:
            lvl = int(cr.get("level", 1))
            name = str(cr.get("name", "?"))
            w = cr.get("_weapon") if isinstance(cr.get("_weapon"), dict) else None
            w_name = str(w.get("name", "")) if w else None
            w_part = f" \u2022 **{w_name}**" if w_name else ""
            enemy_lines.append(f"Lv.{lvl} {name}{w_part}")

        embed.add_field(name="🛡️ Your Team", value="\\n".join(team_lines) if team_lines else "None", inline=True)
        embed.add_field(name="👾 Enemy Team", value="\\n".join(enemy_lines) if enemy_lines else "None", inline=True)
        
        # Add Combat Stats and MVP
        stats_text = ""
        if mvp_creature:
            stats_text += f"**MVP:** {mvp_creature['name']} ({mvp_creature['damage']} DMG, {mvp_creature['kills']} Kills)\\n"
        stats_text += f"**Dealt:** {damage_dealt:,}  |  **Taken:** {damage_taken:,}\\n"
        stats_text += f"**Crits:** {crits}  |  **Statuses:** {status_applied}"
        
        embed.add_field(name="📊 Combat Summary", value=stats_text, inline=False)
        
        embed.set_image(url="attachment://abyssia_battle.png")"""

# Find the start and end patterns
start_idx = content.find("        team_lines = []")
end_idx = content.find("        if battle_message is not None:")

if start_idx != -1 and end_idx != -1:
    new_content = content[:start_idx] + new_str + "\n" + content[end_idx:]
    path.write_text(new_content, encoding="utf-8")
    print("Successfully replaced.")
else:
    print("Could not find start or end index.")
