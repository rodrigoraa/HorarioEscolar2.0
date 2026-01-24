import pandas as pd
from io import BytesIO

def gerar_modelo_excel():
    """
    Gera um arquivo Excel de exemplo na memória (buffer) 
    para o usuário baixar.
    """
    output = BytesIO()
    
    # --- 1. Dados da Aba 'Turmas' ---
    df_turmas = pd.DataFrame([
        {'Turma': '6º Ano A', 'Aulas_Semanais': 25},
        {'Turma': '7º Ano B', 'Aulas_Semanais': 25},
        {'Turma': '1º Ano Médio', 'Aulas_Semanais': 30},
        {'Turma': '2º Ano Médio', 'Aulas_Semanais': 30},
    ])
    
    # --- 2. Dados da Aba 'Grade_Curricular' ---
    df_grade = pd.DataFrame([
        {
            'Professor': 'Ana Silva', 
            'Materia': 'Matemática', 
            'Turmas_Alvo': '6º Ano A, 7º Ano B', 
            'Aulas_Por_Turma': 4, 
            'Indisponibilidade': 'Seg, Ter'
        },
        {
            'Professor': 'Carlos Souza', 
            'Materia': 'História', 
            'Turmas_Alvo': '6º Ano A', 
            'Aulas_Por_Turma': 2, 
            'Indisponibilidade': ''
        },
        {
            'Professor': 'Beatriz Lima', 
            'Materia': 'Física', 
            'Turmas_Alvo': '1º Ano Médio, 2º Ano Médio', 
            'Aulas_Por_Turma': 3, 
            'Indisponibilidade': 'Sex:1'
        }
    ])
    
    # --- 3. Escrita no Excel ---
    # Usa o 'xlsxwriter' para poder formatar larguras de coluna
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        
        # Aba Turmas
        df_turmas.to_excel(writer, sheet_name='Turmas', index=False)
        # Ajuste de largura visual
        worksheet = writer.sheets['Turmas']
        worksheet.set_column('A:A', 20) # Coluna Turma mais larga
        worksheet.set_column('B:B', 15)
        
        # Aba Grade
        df_grade.to_excel(writer, sheet_name='Grade_Curricular', index=False)
        # Ajuste de largura visual
        worksheet = writer.sheets['Grade_Curricular']
        worksheet.set_column('A:B', 20) # Prof e Materia
        worksheet.set_column('C:C', 30) # Turmas (precisa ser largo)
        worksheet.set_column('D:E', 18)

    return output.getvalue()