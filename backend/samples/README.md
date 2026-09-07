# 后台导入示例文件

这些 CSV 可用于在管理后台测试批量导入。

## 推荐导入顺序

1. 先导入 `institutions_sample.csv`：新增两所示例院校。
2. 再导入 `majors_sample.csv`：新增两个示例专业。
3. 导入 `institution_majors_sample.csv`：南京邮电大学的计算机技术组合已存在，会更新。
4. 导入 `admission_stats_sample.csv`：为南京邮电大学计算机技术补充 2024/2025 两年示例招录数据。

## 使用方法

1. 启动后端。
2. 打开 <http://127.0.0.1:8000/admin.html>。
3. 在「批量导入」中选择对应数据类型与文件。
4. 点「开始导入」。
