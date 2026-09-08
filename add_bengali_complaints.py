import pandas as pd

# List of Bengali transliterated (Banglish) complaints mapped to products
bengali_complaints = [
    # Electricity
    ("light chole geche", "Electricity"),
    ("current kete geche", "Electricity"),
    ("bijli nei", "Electricity"),
    ("amader ekhane current nei", "Electricity"),
    ("line kete geche", "Electricity"),
    ("transformer e agun legeche", "Electricity"),
    ("wire chire geche", "Electricity"),
    ("load shedding hocche khub", "Electricity"),
    ("light blink korche bar bar", "Electricity"),
    ("meter e line asche na", "Electricity"),
    ("tar chire rastaye pore ache", "Electricity"),
    ("bijli chole geche", "Electricity"),
    
    # Water Supply
    ("jol asche na kol e", "Water Supply"),
    ("kol e jol nei", "Water Supply"),
    ("joler pipe leak korche", "Water Supply"),
    ("pipe phete jol berocche", "Water Supply"),
    ("nongra jol asche tap e", "Water Supply"),
    ("jol er line e leakage ache", "Water Supply"),
    ("khabar jol nei amader ekhane", "Water Supply"),
    ("jol er pipe line bhenge geche", "Water Supply"),
    ("tanki te jol nei", "Water Supply"),
    ("joler supply bondho", "Water Supply"),
    
    # Sanitation
    ("nongra hoye ache charidik", "Sanitation"),
    ("aborjana porishkar korar lok nei", "Sanitation"),
    ("toilet khub nongra", "Sanitation"),
    ("gondho berocche nardama theke", "Sanitation"),
    ("nongra aborjana jome ache", "Sanitation"),
    ("dustbin porishkar kora dorkar", "Sanitation"),
    ("porishkar porichonnotar অভাব", "Sanitation"),
    ("goli nongra hoye ache", "Sanitation"),
    
    # Road Maintenance
    ("rasta kharap khub", "Road Maintenance"),
    ("rastaye khub gorto hoyeche", "Road Maintenance"),
    ("rasta bhenge geche puro", "Road Maintenance"),
    ("gorto hoye ache pitch rastaye", "Road Maintenance"),
    ("rasta thik kora dorkar", "Road Maintenance"),
    ("rastaye chola jacche na gorto jonno", "Road Maintenance"),
    ("broken road repair chai", "Road Maintenance"),
    ("rasta repair kora hok", "Road Maintenance"),
    
    # Public Lighting
    ("street light jolche na", "Public Lighting"),
    ("post er light bondho", "Public Lighting"),
    ("rastaye andhar hoye ache light chara", "Public Lighting"),
    ("street light repair kora dorkar", "Public Lighting"),
    ("bulb kharup street light er", "Public Lighting"),
    ("rastar light jolche na ratre", "Public Lighting"),
    
    # Gas Leaks
    ("gas leak hocche smell asche", "Gas Leaks"),
    ("gaser gondho berocche cylinder theke", "Gas Leaks"),
    ("gas pipeline leak korche", "Gas Leaks"),
    ("cylinder theke gas leak korche mone hocche", "Gas Leaks"),
    
    # Noise
    ("loud speaker er awaj khub besi", "Noise"),
    ("jore dj box bajano hocche", "Noise"),
    ("mic er joralo awaj", "Noise"),
    ("noise pollution hocche ratre", "Noise"),
    ("sound box khub jore bajche", "Noise"),
    
    # Waste Management
    ("kachra phelche rastaye shobai", "Waste Management"),
    ("kachrar gari aseni koyekdin", "Waste Management"),
    ("dustbin e aborjana vorte", "Waste Management"),
    ("waste management khub kharap", "Waste Management"),
    
    # Drainage
    ("nardama bondho hoye geche", "Drainage"),
    ("drain er jol rastaye jome geche", "Drainage"),
    ("drain jam hoye geche puro", "Drainage"),
    ("nongra jol overflow hocche drain theke", "Drainage"),
    ("drain clean kora dorkar", "Drainage"),
    
    # Traffic
    ("traffic jam khub besi ekhane", "Traffic"),
    ("rasta jam hoye ache gaari cholche na", "Traffic"),
    ("traffic signal kaj korche na", "Traffic"),
    ("signal light bondho hoye ache", "Traffic")
]

# Read existing complaints
df = pd.read_csv('consumer_complaints.csv')

# Create new DataFrame for Bengali complaints
new_rows = pd.DataFrame(bengali_complaints, columns=['complaint_text', 'product'])

# Concat and save
updated_df = pd.concat([df, new_rows], ignore_index=True)
updated_df.to_csv('consumer_complaints.csv', index=False)
print(f"✅ Added {len(new_rows)} Bengali transliterated complaints to consumer_complaints.csv")
