# exporters.py
import pandas as pd
import io
import xlsxwriter

def gerar_excel_colorido(resultados, dias_list):
    """
    Gera um Excel estilo 'Corporativo/Clean':
    - Sem cores de fundo nas matérias.
    - Cabeçalhos em cinza suave.
    - Foco na legibilidade e impressão.
    """
    output = io.BytesIO()
    df_resultados = pd.DataFrame(resultados)

    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        
        # --- ESTILOS PROFISSIONAIS (B&W) ---
        
        # 1. Estilo para o Cabeçalho (Dias da Semana)
        fmt_header = workbook.add_format({
            'bold': True,
            'font_size': 11,
            'bg_color': '#F2F2F2', # Cinza muito suave
            'font_color': '#000000',
            'border': 1,
            'border_color': '#bfbfbf', # Borda cinza médio
            'align': 'center',
            'valign': 'vcenter'
        })
        
        # 2. Estilo para a Coluna de Horários (1ª Aula, 2ª Aula...)
        fmt_index = workbook.add_format({
            'bold': True,
            'font_size': 10,
            'bg_color': '#F2F2F2',
            'border': 1,
            'border_color': '#bfbfbf',
            'align': 'center',
            'valign': 'vcenter'
        })

        # 3. Estilo para o Conteúdo (Matéria/Prof) - Fundo Branco Limpo
        fmt_celula = workbook.add_format({
            'font_size': 10,
            'text_wrap': True,    # Quebra de linha automática
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'border_color': '#bfbfbf'
        })

        turmas_unicas = sorted(list(set(df_resultados['turma'])))
        
        for turma in turmas_unicas:
            # Filtra dados da turma
            df_t = df_resultados[df_resultados['turma'] == turma]
            
            # Prepara a matriz de dados
            rows = [f"{i+1}ª Aula" for i in range(6)]
            grade_visual = pd.DataFrame("", index=rows, columns=dias_list)

            for _, row in df_t.iterrows():
                d_idx = row['dia_idx']
                a_idx = row['aula_idx']
                # Formato: MATÉRIA (linha de cima) / Prof (linha de baixo)
                conteudo = f"{row['materia']}\n({row['prof']})"
                grade_visual.iat[a_idx, d_idx] = conteudo

            # Nome da aba (limpeza de caracteres inválidos)
            sheet_name = turma.replace(":", "").replace("/", "").strip()[:30]
            
            # Escreve os dados
            grade_visual.to_excel(writer, sheet_name=sheet_name)
            worksheet = writer.sheets[sheet_name]
            
            # --- APLICAÇÃO MANUAL DOS ESTILOS ---
            
            # 1. Formatar Cabeçalhos (Linha 0)
            for col_num, value in enumerate(grade_visual.columns.values):
                # Escreve o cabeçalho (Seg, Ter...) com estilo cinza
                worksheet.write(0, col_num + 1, value, fmt_header)
                
            # 2. Formatar Índice (Coluna 0) e Células de Dados
            for row_num in range(len(rows)):
                # Escreve o índice (1ª Aula...) com estilo cinza
                worksheet.write(row_num + 1, 0, rows[row_num], fmt_index)
                
                # Escreve os dados (Matéria) com fundo branco e borda
                for col_num in range(len(dias_list)):
                    conteudo = grade_visual.iloc[row_num, col_num]
                    worksheet.write(row_num + 1, col_num + 1, conteudo, fmt_celula)

            # --- AJUSTES DE LARGURA/ALTURA ---
            # Coluna A (Horários) mais estreita
            worksheet.set_column(0, 0, 15)
            # Colunas B em diante (Dias) mais largas
            worksheet.set_column(1, len(dias_list), 25)
            # Altura das linhas um pouco maior para caber o texto duplo
            for row_num in range(1, len(rows) + 1):
                worksheet.set_row(row_num, 45) # Altura 45 (cabe duas linhas folgadas)

    return output.getvalue()