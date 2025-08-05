#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos_v2  
@FileName   : fix_csv_data_types.py
@Date       : 2025/8/5
@Author     : Claude
@Description: 修复CSV文件数据类型问题的脚本
"""

import polars as pl
from pathlib import Path
import time
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_tick_csv_files(base_path: Path):
    """修复tick CSV文件的数据类型"""
    tick_csv_path = base_path / "tick_csv"
    
    if not tick_csv_path.exists():
        logger.warning(f"Tick CSV路径不存在: {tick_csv_path}")
        return
    
    # 定义tick数据的正确数据类型
    tick_schema = {
        'InstrumentID': pl.Utf8,
        'ExchangeID': pl.Utf8,
        'TradingDay': pl.Utf8,
        'UpdateTime': pl.Utf8,
        'UpdateMillisec': pl.Int64,
        'PreSettlementPrice': pl.Float64,
        'PreClosePrice': pl.Float64,
        'PreOpenInterest': pl.Float64,
        'OpenPrice': pl.Float64,
        'ClosePrice': pl.Float64,
        'SettlementPrice': pl.Float64,
        'UpperLimitPrice': pl.Float64,
        'LowerLimitPrice': pl.Float64,
        'HighestPrice': pl.Float64,
        'LowestPrice': pl.Float64,
        'LastPrice': pl.Float64,
        'Volume': pl.Float64,
        'LastVolume': pl.Float64,
        'Turnover': pl.Float64,
        'OpenInterest': pl.Float64,
        'LastOpenInterest': pl.Float64,
        'BidPrice1': pl.Float64,
        'BidVolume1': pl.Float64,
        'AskPrice1': pl.Float64,
        'AskVolume1': pl.Float64,
        'BidPrice2': pl.Float64,
        'BidVolume2': pl.Float64,
        'AskPrice2': pl.Float64,
        'AskVolume2': pl.Float64,
        'BidPrice3': pl.Float64,
        'BidVolume3': pl.Float64,
        'AskPrice3': pl.Float64,
        'AskVolume3': pl.Float64,
        'BidPrice4': pl.Float64,
        'BidVolume4': pl.Float64,
        'AskPrice4': pl.Float64,
        'AskVolume4': pl.Float64,
        'BidPrice5': pl.Float64,
        'BidVolume5': pl.Float64,
        'AskPrice5': pl.Float64,
        'AskVolume5': pl.Float64,
        'AveragePrice': pl.Float64,
        'symbol': pl.Utf8,
        'exchange': pl.Utf8,
        'datetime': pl.Utf8
    }
    
    total_files = 0
    fixed_files = 0
    
    # 遍历所有日期目录
    for date_dir in tick_csv_path.iterdir():
        if not date_dir.is_dir():
            continue
            
        logger.info(f"处理日期目录: {date_dir.name}")
        
        # 遍历该日期下的所有CSV文件
        for csv_file in date_dir.glob("*.csv"):
            if csv_file.name.startswith('.') or 'backup_' in csv_file.name:
                continue  # 跳过隐藏文件和备份文件
                
            total_files += 1
            
            try:
                # 读取CSV文件，指定数据类型
                df = pl.read_csv(csv_file, schema_overrides=tick_schema)
                
                # 创建临时文件
                temp_file = csv_file.with_suffix('.fixed_tmp')
                
                # 写入修复后的数据
                df.write_csv(temp_file)
                
                # 备份原文件
                backup_file = csv_file.with_suffix(f'.backup_fixed_{int(time.time())}.csv')
                csv_file.rename(backup_file)
                
                # 将临时文件移动为正式文件
                temp_file.rename(csv_file)
                
                fixed_files += 1
                logger.info(f"已修复: {csv_file.name}")
                
            except Exception as e:
                logger.error(f"修复文件失败 {csv_file.name}: {e}")
    
    logger.info(f"Tick CSV文件处理完成，总文件数: {total_files}，成功修复: {fixed_files}")

def fix_bar_csv_files(base_path: Path):
    """修复bar CSV文件的数据类型"""
    bar_csv_path = base_path / "bar_csv"
    
    if not bar_csv_path.exists():
        logger.warning(f"Bar CSV路径不存在: {bar_csv_path}")
        return
    
    # 定义bar数据的正确数据类型
    bar_schema = {
        'BarType': pl.Utf8,
        'UpdateTime': pl.Utf8,
        'InstrumentID': pl.Utf8,
        'Volume': pl.Float64,
        'OpenInterest': pl.Float64,
        'OpenPrice': pl.Float64,
        'HighestPrice': pl.Float64,
        'LowestPrice': pl.Float64,
        'ClosePrice': pl.Float64,
        'LastVolume': pl.Float64,
        'symbol': pl.Utf8,
        'exchange': pl.Utf8,
        'datetime': pl.Utf8
    }
    
    total_files = 0
    fixed_files = 0
    
    # 遍历所有日期目录
    for date_dir in bar_csv_path.iterdir():
        if not date_dir.is_dir():
            continue
            
        logger.info(f"处理日期目录: {date_dir.name}")
        
        # 遍历该日期下的所有CSV文件
        for csv_file in date_dir.glob("*.csv"):
            if csv_file.name.startswith('.') or 'backup_' in csv_file.name:
                continue  # 跳过隐藏文件和备份文件
                
            total_files += 1
            
            try:
                # 读取CSV文件，指定数据类型
                df = pl.read_csv(csv_file, schema_overrides=bar_schema)
                
                # 创建临时文件
                temp_file = csv_file.with_suffix('.fixed_tmp')
                
                # 写入修复后的数据
                df.write_csv(temp_file)
                
                # 备份原文件
                backup_file = csv_file.with_suffix(f'.backup_fixed_{int(time.time())}.csv')
                csv_file.rename(backup_file)
                
                # 将临时文件移动为正式文件
                temp_file.rename(csv_file)
                
                fixed_files += 1
                logger.info(f"已修复: {csv_file.name}")
                
            except Exception as e:
                logger.error(f"修复文件失败 {csv_file.name}: {e}")
    
    logger.info(f"Bar CSV文件处理完成，总文件数: {total_files}，成功修复: {fixed_files}")

def main():
    """主函数"""
    print("🔧 Homalos CSV数据类型修复工具")
    print("=" * 50)
    
    # 数据目录
    data_path = Path("data")
    
    if not data_path.exists():
        logger.error(f"数据目录不存在: {data_path}")
        return
    
    logger.info("开始修复CSV文件数据类型...")
    
    # 修复tick CSV文件
    logger.info("🎯 修复tick CSV文件...")
    fix_tick_csv_files(data_path)
    
    # 修复bar CSV文件  
    logger.info("🎯 修复bar CSV文件...")
    fix_bar_csv_files(data_path)
    
    logger.info("✅ CSV文件数据类型修复完成!")
    print("\n注意事项:")
    print("1. 原文件已备份为 .backup_fixed_timestamp.csv")
    print("2. 现在重新启动数据中心应该不会再出现数据类型冲突问题")
    print("3. 如果需要，可以手动删除备份文件以节省空间")

if __name__ == "__main__":
    main()