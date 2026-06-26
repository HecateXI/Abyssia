from __future__ import annotations

from collections.abc import Iterable, Sequence

import discord

from core.card_controls import CardShortcut, CommandShortcutButton, shortcut_label_blocked


SectionLike = tuple[str, str]
ShortcutLike = tuple[str, str] | tuple[str, str, str]


def _as_colour(value: discord.Colour | int | None) -> discord.Colour:
    if isinstance(value, discord.Colour):
        return value
    if isinstance(value, int):
        return discord.Colour(value)
    return discord.Colour.dark_gray()


def _shortcut_items(shortcuts: Iterable[ShortcutLike]) -> list[CardShortcut]:
    items: list[CardShortcut] = []
    for item in shortcuts:
        if shortcut_label_blocked(item[0]):
            continue
        items.append(CardShortcut(label=item[0], command=item[1], description=item[2] if len(item) > 2 else ""))
    return items


class AbyssiaLayoutView(discord.ui.LayoutView):
    """Discord v2 component card: title, large media, compact sections, and buttons."""

    def __init__(
        self,
        *,
        owner_id: int | None = None,
        title: str,
        subtitle: str | None = None,
        image_filename: str | None = None,
        image_description: str | None = None,
        sections: Sequence[SectionLike] = (),
        footer: str | None = None,
        shortcuts: Sequence[ShortcutLike] = (),
        buttons: Sequence[discord.ui.Button] = (),
        accent: discord.Colour | int | None = None,
        timeout: float = 180,
    ) -> None:
        super().__init__(timeout=timeout)
        self.owner_id = owner_id
        colour = _as_colour(accent)
        container = discord.ui.Container(accent_colour=colour)

        header = f"## {title.strip()}"
        if subtitle:
            header += f"\n{subtitle.strip()}"
        container.add_item(discord.ui.TextDisplay(header))

        if image_filename:
            container.add_item(
                discord.ui.MediaGallery(
                    discord.MediaGalleryItem(
                        f"attachment://{image_filename}",
                        description=(image_description or title)[:256],
                    )
                )
            )

        for name, value in sections:
            if not value:
                continue
            container.add_item(discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small))
            container.add_item(discord.ui.TextDisplay(f"**{name}**\n{value}"))

        if footer:
            container.add_item(discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small))
            container.add_item(discord.ui.TextDisplay(footer))

        row_buttons: list[discord.ui.Button] = list(buttons)
        row_buttons.extend(CommandShortcutButton(shortcut) for shortcut in _shortcut_items(shortcuts))
        if row_buttons:
            for start in range(0, min(len(row_buttons), 10), 5):
                row = discord.ui.ActionRow()
                for button in row_buttons[start:start + 5]:
                    row.add_item(button)
                container.add_item(row)

        self.add_item(container)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.owner_id is None or interaction.user.id == self.owner_id:
            return True
        await interaction.response.send_message("These card controls belong to another hunter.", ephemeral=True)
        return False
