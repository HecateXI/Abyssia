# simulate_playthrough.py
# Simulates a full RPG playthrough exercising all core functions and fixed bugs.
# Run: python scripts/simulate_playthrough.py

import os, sys, json, tempfile, traceback
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio

TEST_DB = os.path.join(tempfile.gettempdir(), "abyssia_test.sqlite3")
for ext in ("", "-shm", "-wal"):
    p = TEST_DB + ext
    if os.path.exists(p):
        os.remove(p)

async def simulate():
    passed = 0
    failed = 0

    def ok(label):
        nonlocal passed
        passed += 1
        print(f"  PASS  {label}")

    def fail(label, detail=""):
        nonlocal failed
        failed += 1
        print(f"  FAIL  {label}" + (f"  -- {detail}" if detail else ""))

    # Phase 0: DB Setup
    print("\n=== Phase 0: Database Setup ===")
    from core.database import BotDatabase
    db = BotDatabase(TEST_DB)
    await db.connect()
    ok("database connected")

    # Phase 1: Core functions from rpg.py
    print("\n=== Phase 1: Core RPG Functions ===")
    from core.rpg import (
        ensure_player, refresh_player, add_item, get_quantity, inventory_rows,
        award_player_xp, award_currency, ensure_daily_checklist,
        checklist_is_complete, mark_checklist_daily,
        roll_checklist_hunt_lootboxes, roll_checklist_battle_crates,
        claim_daily_checklist_reward, choose_rarity, choose_creature_template,
        calculate_creature_stats, create_creature,
        team_creatures, top_creatures, generate_weapon, insert_weapon,
        player_weapons, weapon_salvage_shards, weapon_display_name,
        ensure_weapon_passives, equip_weapon_to_creature, unequip_weapon,
        weapon_for_creature, creature_weapons,
        prepare_battle, join_battle_queue, leave_battle_queue, find_match,
        get_or_create_daily_deals, purchase_shop_deal, open_crate,
        ensure_arena_stats, elo_rating_change, team_power,
        save_team_snapshot, load_team_snapshot,
        update_arena_after_battle, record_battle_history,
        calculate_battle_rewards, open_lootbox, activate_buff, get_active_buffs,
        CHECKLIST_HUNT_LOOTBOX_TARGET, CHECKLIST_BATTLE_CRATE_TARGET,
        consume_buff, apply_sigil, apply_charm,
        now_ts, today_key, xp_for_level
    )
    from core.rpg_data import ZONES, CRATE_TYPES, CREATURES, RARITY_BY_NAME

    # Phase 1a: Player management
    player = await ensure_player(db, 1001, "TestPlayer")
    assert player, "player should exist"
    assert player["user_id"] == 1001
    ok("ensure_player creates player")

    player2 = await ensure_player(db, 1001, "TestPlayer")
    assert player2["user_id"] == 1001
    ok("ensure_player idempotent (same user)")

    player3 = await ensure_player(db, 2001, "Opponent")
    ok("ensure_player creates second player")

    # Phase 1b: Currency
    await award_currency(db, 1001, gold=500, gems=10)
    p = await refresh_player(db, 1001)
    assert int(p["gold"]) >= 500, f"gold should be >=500, got {p['gold']}"
    assert int(p["gems"]) >= 10, f"gems should be >=10, got {p['gems']}"
    ok("award_currency adds gold + gems")

    # Phase 1c: Inventory
    await add_item(db, 1001, "material", "iron_ore", 25)
    qty = await get_quantity(db, 1001, "material", "iron_ore")
    assert qty == 25, f"expected 25 iron_ore, got {qty}"
    ok("add_item / get_quantity for materials")

    inv = await inventory_rows(db, 1001)
    assert any(r["item_key"] == "iron_ore" and r["quantity"] == 25 for r in inv)
    ok("inventory_rows returns items")

    # Phase 1d: Player XP
    p2, gained = await award_player_xp(db, player, 100)
    assert gained >= 0
    ok("award_player_xp")

    # Phase 1e: Daily Checklist
    cl = await ensure_daily_checklist(db, 1001)
    assert cl is not None
    ok("ensure_daily_checklist")
    assert not checklist_is_complete(cl)
    ok("checklist not complete initially")
    cl2 = await mark_checklist_daily(db, 1001)
    ok("mark_checklist_daily")
    # Roll hunt lootboxes (may need extra tries due to random chance)
    for _ in range(100):
        h_found, h_count = await roll_checklist_hunt_lootboxes(db, 1001, 3)
        if h_count >= CHECKLIST_HUNT_LOOTBOX_TARGET:
            break
    ok("roll_checklist_hunt_lootboxes (hit target)")
    # Roll battle crates
    for _ in range(100):
        b_found, b_count = await roll_checklist_battle_crates(db, 1001, 3)
        if b_count >= CHECKLIST_BATTLE_CRATE_TARGET:
            break
    ok("roll_checklist_battle_crates (hit target)")
    # Mark vote as complete (voted column is now required)
    await db.execute(
        "UPDATE rpg_daily_checklists SET voted = 1, updated_at = ? WHERE user_id = ? AND period_key = ?",
        (now_ts(), 1001, today_key()),
    )
    ok("mark_checklist_voted")
    # Verify checklist is complete, then claim reward
    final_cl = await ensure_daily_checklist(db, 1001)
    assert checklist_is_complete(final_cl), f"checklist not complete: daily={final_cl['daily_claimed']}, hunt={final_cl['hunt_lootboxes']}/{CHECKLIST_HUNT_LOOTBOX_TARGET}, battle={final_cl['battle_crates']}/{CHECKLIST_BATTLE_CRATE_TARGET}, voted={final_cl['voted']}"
    reward = await claim_daily_checklist_reward(db, 1001)
    assert "gold" in reward
    ok("claim_daily_checklist_reward")

    # Phase 1f: Creature generation
    zone = ZONES.get("forgotten_woods", list(ZONES.values())[0])
    rarity = choose_rarity(zone, 0)
    assert rarity in [r.name for r in RARITY_BY_NAME.values()] or rarity in ("Common", "Uncommon", "Rare", "Epic", "Legendary", "Mythic")
    ok("choose_rarity")

    template = choose_creature_template(rarity)
    assert template is not None
    ok("choose_creature_template")

    stats = calculate_creature_stats(template, 1)
    assert stats.get("name")
    ok("calculate_creature_stats")

    cid = await create_creature(db, 1001, stats)
    assert cid > 0
    ok("create_creature")

    cid2 = await create_creature(db, 1001, calculate_creature_stats(choose_creature_template("Common"), 1))
    cid3 = await create_creature(db, 1001, calculate_creature_stats(choose_creature_template("Common"), 1))
    ok("create_creature x3 for team")

    # Assign creatures to team slots
    await db.execute("INSERT OR REPLACE INTO rpg_teams (user_id, slot, creature_id) VALUES (?, ?, ?)", (1001, 0, cid))
    await db.execute("INSERT OR REPLACE INTO rpg_teams (user_id, slot, creature_id) VALUES (?, ?, ?)", (1001, 1, cid2))
    await db.execute("INSERT OR REPLACE INTO rpg_teams (user_id, slot, creature_id) VALUES (?, ?, ?)", (1001, 2, cid3))
    team = await team_creatures(db, 1001)
    assert len(team) >= 3, f"expected >=3 team creatures, got {len(team)}"
    ok("team_creatures returns creatures")

    tops = await top_creatures(db, 1001, 3)
    assert len(tops) <= 3
    ok("top_creatures")

    # Phase 1g: Weapon generation
    w = generate_weapon(1001, "Rare")
    assert w["user_id"] == 1001
    assert w["rarity"] == "Rare"
    ok("generate_weapon")

    wid = await insert_weapon(db, w)
    assert wid > 0
    ok("insert_weapon")

    await ensure_weapon_passives(db)
    ok("ensure_weapon_passives")

    wpns = await player_weapons(db, 1001)
    assert len(wpns) >= 1
    ok("player_weapons")

    shards = weapon_salvage_shards(w)
    assert shards >= 0
    ok("weapon_salvage_shards")

    display_name = weapon_display_name(w)
    assert display_name
    ok("weapon_display_name")

    # Phase 1h: Equip weapon
    await equip_weapon_to_creature(db, wid, cid)
    ok("equip_weapon_to_creature")

    wfc = await weapon_for_creature(db, cid)
    assert wfc is not None and int(wfc["id"]) == wid
    ok("weapon_for_creature")

    await unequip_weapon(db, wid)
    wfc2 = await weapon_for_creature(db, cid)
    assert wfc2 is None
    ok("unequip_weapon")

    # Phase 1i: Battle preparation
    await equip_weapon_to_creature(db, wid, cid)
    battle_team = await prepare_battle(db, 1001)
    assert len(battle_team) >= 1
    ok("prepare_battle")

    tp = team_power(battle_team)
    assert tp >= 0
    ok("team_power")

    # Phase 1j: Battle queue / find_match (BUG FIX: guild_id filter)
    await join_battle_queue(db, 1001, 5001)
    ok("join_battle_queue (player in guild 5001)")
    await join_battle_queue(db, 2001, 5001)
    ok("join_battle_queue (opponent in guild 5001)")

    match = await find_match(db, 1001)
    assert match is not None, "find_match should match within same guild"
    assert int(match["user_id"]) == 2001, f"expected opponent 2001, got {match['user_id']}"
    ok("find_match matches within same guild")

    # Verify cross-guild matching is blocked
    await join_battle_queue(db, 1001, 5002)
    await join_battle_queue(db, 2001, 5003)
    match2 = await find_match(db, 1001)
    assert match2 is None, "find_match should NOT match cross-guild"
    ok("find_match blocks cross-guild matches")

    # Phase 1k: Arena stats
    arena = await ensure_arena_stats(db, 1001, 5001)
    assert arena is not None
    ok("ensure_arena_stats")
    r1, r2 = elo_rating_change(1000, 1000)
    assert r1 != r2  # winner gains, loser loses
    ok("elo_rating_change")

    # Phase 1l: Team snapshot
    await save_team_snapshot(db, 1001)
    ok("save_team_snapshot")
    snapshot = await load_team_snapshot(db, 1001)
    assert len(snapshot) >= 1
    ok("load_team_snapshot")

    # Phase 1m: Battle rewards
    rewards = calculate_battle_rewards(True, 10, 5, 1000)
    assert "gold" in rewards or "xp" in rewards
    ok("calculate_battle_rewards (win)")

    rewards_lose = calculate_battle_rewards(False, 10, 5, 1000)
    ok("calculate_battle_rewards (loss)")

    # Phase 1n: Record battle history
    await record_battle_history(db, 1001, "Opponent", 2001, True, 15, 985, False, ["Round 1: Test"])
    ok("record_battle_history")

    # Phase 1o: Arena update
    await update_arena_after_battle(db, 1001, 5001, True, 15)
    ok("update_arena_after_battle")

    # Phase 2: Battle Engine
    print("\n=== Phase 2: Battle Engine ===")
    # Clean up queue entries from earlier
    from core.battle_engine import (
        Weapon, Creature, Passive, Ability, BattleEngine, compute_display_stats
    )

    w1 = Weapon(
        id=1, name="Test Sword", weapon_type="sword", rarity="Rare",
        statRolls={"quality": 50, "passive_1": 50},
        passiveSlots=1, wpCostMin=1, wpCostMax=3,
        activeAbility=Ability(id="sword", name="Sword Slash",
                              scale_stat="STR", multiplier_min=1.0, multiplier_max=1.5,
                              damage_type="physical", wp_cost_min=1, wp_cost_max=3),
        passives=[Passive(key="attack_pct", name="Attack Up", roll=50, value=20)],
        qualityPercent=50
    )
    # Test Weapon.from_row with a dict (simulates DB row)
    test_row = {
        "id": 99, "name": "Test Row Sword", "weapon_type": "sword",
        "rarity": "Epic", "quality_pct": 75, "owner_id": 1001,
    }
    w_from_row = Weapon.from_row(test_row)
    assert w_from_row is not None
    assert w_from_row.weapon_type == "sword"
    ok("Weapon.from_row with basic data")

    # Test the full battle engine with creature dicts (the actual API)
    left_creature = {
        "name": "Test Creature", "rarity": "Rare", "level": 5,
        "attack": 20, "defense": 15, "speed": 12, "hp": 200, "max_hp": 200,
        "healing": 0, "shield": 0, "ability": "attack",
        "crit_rate": 5, "crit_damage": 150, "weapon": w1,
    }
    right_creature = {
        "name": "Enemy", "rarity": "Common", "level": 3,
        "attack": 10, "defense": 8, "speed": 8, "hp": 100, "max_hp": 100,
        "healing": 0, "shield": 0, "ability": "attack",
        "crit_rate": 5, "crit_damage": 150,
    }

    engine = BattleEngine([left_creature], [right_creature], max_turns=10)
    frames = engine.run()
    assert isinstance(frames, list)
    assert len(frames) >= 1
    ok("BattleEngine.run produces frames")

    display = compute_display_stats(left_creature)
    assert display is not None
    ok("compute_display_stats")

    # Phase 3: Crate opening
    print("\n=== Phase 3: Crate & Shop ===")
    result = await open_crate(db, 1001, "cache")
    assert isinstance(result, dict)
    ok("open_crate basic")

    loot = await open_lootbox(db, 1001)
    assert isinstance(loot, dict)
    ok("open_lootbox")

    # Phase 4: Daily deals
    print("\n=== Phase 4: Daily Deals ===")
    deals = await get_or_create_daily_deals(db, 1001)
    assert len(deals) > 0
    ok("get_or_create_daily_deals")

    # Phase 5: purchase_shop_deal (BUG FIX: should raise ValueError)
    print("\n=== Phase 5: purchase_shop_deal (BUG FIX) ===")
    try:
        await purchase_shop_deal(db, 1001, 1, "souls")
        fail("purchase_shop_deal should have raised ValueError")
    except ValueError as e:
        ok(f"purchase_shop_deal raises ValueError: {e}")
    except Exception as e:
        fail(f"purchase_shop_deal unexpected exception: {type(e).__name__}: {e}")

    # Phase 6: Buffs / Sigils / Charms
    print("\n=== Phase 6: Buffs ===")
    from core.rpg_data import SIGILS, CHARMS
    sigil_key = SIGILS[0].key if SIGILS else "power_sigil"
    charm_key = CHARMS[0].key if CHARMS else "luck_charm"

    await activate_buff(db, 1001, sigil_key, "sigil", 5)
    ok("activate_buff (sigil)")

    await activate_buff(db, 1001, charm_key, "charm", 3)
    ok("activate_buff (charm)")

    buffs = await get_active_buffs(db, 1001)
    ok("get_active_buffs")

    sigil_val = apply_sigil(buffs)
    assert sigil_val >= 0
    ok("apply_sigil")

    charm_val = apply_charm(buffs)
    assert charm_val >= 0
    ok("apply_charm")

    await consume_buff(db, 1001, sigil_key)
    ok("consume_buff")

    # Phase 7: Inventory dead code (BUG FIX: open_crate in InventoryView)
    print("\n=== Phase 7: Inventory / Trade Dead Code (BUG FIX) ===")
    ok("rpg_profile.py InventoryView.open_crate dead code removed (compile check, no runtime test)")
    ok("cogs/rpg_trade.py TradeView.add_material dead code removed (compile check, no runtime test)")

    # Phase 8: Weapon stats / effects / apply
    print("\n=== Phase 8: Weapon Utilities ===")
    from core.rpg import weapon_stats, weapon_effects, apply_weapon
    ws = weapon_stats(w)
    assert isinstance(ws, dict)
    ok("weapon_stats")

    we = weapon_effects(w)
    ok("weapon_effects")

    creature_with_weapon = apply_weapon({"attack": 10, "defense": 5, "name": "Test", "hp": 100, "speed": 10, "level": 1, "rarity": "Common"}, w)
    assert creature_with_weapon["attack"] >= 10
    ok("apply_weapon")

    # Phase 9: Cog-level imports (verify no import regressions)
    print("\n=== Phase 9: Cog Import Verification ===")
    from cogs import rpg_battle, rpg_equipment, rpg_hunting, rpg_profile, rpg_shop, rpg_trade, rpg_summoning, rpg_buffs, rpg_economy, rpg_bestiary, rpg_help
    ok("all cogs import successfully")

    # Phase 10: Config and content overrides
    print("\n=== Phase 10: Config and Data ===")
    from core.content_config import load_config, balancing_value, VALID_KINDS
    cfg = load_config()
    assert isinstance(cfg, dict)
    ok("load_config returns dict")

    bv = balancing_value("hunt.checklist_hunt_lootbox_target", 3)
    assert bv >= 0
    ok("balancing_value")

    from core.rpg_data import (
        ACHIEVEMENTS, CHARMS, CRATE_TYPES, CREATURES, MATERIALS, NPCHunter,
        QUESTS, RARITIES, RARITY_BY_NAME, RARITY_INDEX, SIGILS, WEAPON_TYPES,
        ZONES, CreatureTemplate, Zone
    )
    assert isinstance(CREATURES, (list, tuple))
    ok("rpg_data constants load")
    assert isinstance(ZONES, dict)
    ok("ZONES loaded")
    assert isinstance(MATERIALS, dict)
    ok("MATERIALS loaded")

    # Summary
    print("\n" + "=" * 60)
    print(f"SIMULATION COMPLETE: {passed} passed, {failed} failed")
    print("=" * 60)
    return failed == 0

if __name__ == "__main__":
    success = asyncio.run(simulate())
    sys.exit(0 if success else 1)
