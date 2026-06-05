import discord

try:
    @discord.ui.select(placeholder="test", options=[])
    async def my_select(self, interaction, select):
        pass
    print("Success")
except Exception as e:
    print("Error:", type(e), e)
