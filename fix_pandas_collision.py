with open('app.py', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace(
    'grouped = df_filtered.groupby(x_columns)[y_column].agg(agg_func).reset_index()',
    'grouped = df_filtered.groupby(x_columns)[y_column].agg(agg_func).rename("valor_agg").reset_index()'
)

text = text.replace(
    'c_grouped = df_filtered.groupby(cliente_column)[y_column].agg(agg_func).reset_index()',
    'c_grouped = df_filtered.groupby(cliente_column)[y_column].agg(agg_func).rename("valor_agg").reset_index()'
)

text = text.replace('values = grouped[y_column].tolist()', 'values = grouped["valor_agg"].tolist()')
text = text.replace('cliente_values = c_grouped[y_column].tolist()', 'cliente_values = c_grouped["valor_agg"].tolist()')
text = text.replace('c_grouped = c_grouped.sort_values(by=y_column', 'c_grouped = c_grouped.sort_values(by="valor_agg"')

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("Pandas collision fixed")
