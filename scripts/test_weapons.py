from core.battle_engine import BattleEngine

weapon_modes = ['sword', 'bow', 'axe', 'dagger', 'crossbow', 'staff', 'staff_of_purity',
                'shield', 'hammer', 'orb', 'soulreaper', 'briar_relic', 'rot_chalice',
                'banner', 'eye', 'judgement_blade', 'lantern', 'mirror_relic', 'final_bell_scythe']

for wtype in weapon_modes:
    engine = BattleEngine(
        [{'name': 'P1', 'rarity': 'Common', 'level': 10,
          'str_stat': 20, 'hp_stat': 50, 'pr_stat': 10, 'wp_stat': 30, 'mag_stat': 25, 'mr_stat': 8, 'spd': 10,
          '_weapon': {'weapon_type': wtype, 'quality_pct': 50, 'rarity': 'Rare'}}],
        [{'name': 'E1', 'rarity': 'Common', 'level': 5,
          'str_stat': 15, 'hp_stat': 30, 'pr_stat': 5, 'wp_stat': 15, 'mag_stat': 10, 'mr_stat': 5, 'spd': 8}],
        log_enabled=True
    )
    frames = engine.run()
    ability_uses = [e for e in engine.events if e.action not in ('', 'regen', 'energize', 'charge') and e.action_type not in ('basic_attack_debug',)]
    ability_names = set(e.action for e in ability_uses)
    print(f'{wtype:20s} turns={frames[-1]["turn"]:2d} abilities={ability_names}')

print('ALL WEAPON TYPES RAN SUCCESSFULLY')
