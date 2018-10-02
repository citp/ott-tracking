from GhosteryListParser import GhosteryListParser

parser = GhosteryListParser('bugs.json', categorical_blocking=True)
print parser.should_block('https://www.google-analytics.com')
#print parser.should_block('https://www.google-analytics.com/analytics.js')
#print parser.get_block_class('https://www.google-analytics.com/analytics.js')
#print parser.get_classes_description()
