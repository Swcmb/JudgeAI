"""
读取ApplicationForm.xlsx文件并分析数据结构
"""

import pandas as pd
import json

def analyze_excel_file():
    """分析Excel文件结构"""
    try:
        # 读取Excel文件
        print("正在读取 ApplicationForm.xlsx...")
        
        # 尝试读取所有工作表
        excel_file = pd.ExcelFile('ApplicationForm.xlsx')
        print(f"发现工作表: {excel_file.sheet_names}")
        
        for sheet_name in excel_file.sheet_names:
            print(f"\n=== 工作表: {sheet_name} ===")
            
            # 读取工作表
            df = pd.read_excel('ApplicationForm.xlsx', sheet_name=sheet_name)
            
            print(f"数据形状: {df.shape} (行数: {df.shape[0]}, 列数: {df.shape[1]})")
            print(f"列名: {list(df.columns)}")
            
            # 显示前几行数据
            print("\n前5行数据:")
            print(df.head().to_string())
            
            # 检查数据类型
            print(f"\n数据类型:")
            for col in df.columns:
                print(f"  {col}: {df[col].dtype}")
            
            # 检查缺失值
            print(f"\n缺失值统计:")
            missing_data = df.isnull().sum()
            for col, missing_count in missing_data.items():
                if missing_count > 0:
                    print(f"  {col}: {missing_count} 个缺失值")
            
            # 保存为CSV以便查看
            csv_filename = f"{sheet_name}_data.csv"
            df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
            print(f"\n数据已保存为: {csv_filename}")
            
            print("-" * 50)
        
        print("\n✅ Excel文件分析完成!")
        
    except Exception as e:
        print(f"❌ 读取Excel文件失败: {e}")
        print("请确保文件存在且格式正确")

if __name__ == "__main__":
    analyze_excel_file()