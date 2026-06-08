"""Battle-related discord.ui.View classes: challenge accept/decline, revenge."""
from __future__ import annotations

import discord


class BattleChallengeView(discord.ui.View):
    def __init__(self, challenger_id: int, opponent_id: int) -> None:
        super().__init__(timeout=60)
        self.challenger_id = challenger_id
        self.opponent_id = opponent_id
        self.accepted = False
        self.declined = False

    async def _check_user(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.opponent_id:
            await interaction.response.send_message("Only the challenged hunter can answer this duel.", ephemeral=True)
            return False
        return True

    def _disable(self) -> None:
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.danger)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not await self._check_user(interaction):
            return
        self.accepted = True
        self._disable()
        await interaction.response.edit_message(content="Duel accepted. Simulating the battle...", view=self)
        self.stop()

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.secondary)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not await self._check_user(interaction):
            return
        self.declined = True
        self._disable()
        await interaction.response.edit_message(content="Duel declined.", view=self)
        self.stop()


class RevengeView(discord.ui.View):
    def __init__(self, target_id: int) -> None:
        super().__init__(timeout=30)
        self.target_id = target_id
        self.wants_revenge = False

    @discord.ui.button(label="Take Revenge!", style=discord.ButtonStyle.danger)
    async def revenge_btn(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if interaction.user.id != self.target_id:
            await interaction.response.send_message("Not your prompt.", ephemeral=True)
            return
        self.wants_revenge = True
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content="Hunting for a rematch...", view=self)
        self.stop()

    @discord.ui.button(label="Forget it", style=discord.ButtonStyle.secondary)
    async def forget_btn(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if interaction.user.id != self.target_id:
            await interaction.response.send_message("Not your prompt.", ephemeral=True)
            return
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)
        self.stop()
