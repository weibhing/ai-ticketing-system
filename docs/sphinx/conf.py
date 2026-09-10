import sys

sys.path.insert(0, 'C:\\Users\\weibhing\\OneDrive - Intel Corporation\\Documents\\ai-ticketing-system')
sys.path.insert(0, 'C:\\Users\\weibhing\\OneDrive - Intel Corporation\\Documents\\ai-ticketing-system\\app')

project = "AI Ticketing System"
extensions = ["sphinx.ext.autodoc", "sphinx.ext.napoleon"]
autodoc_mock_imports: list[str] = []
html_theme = "alabaster"
