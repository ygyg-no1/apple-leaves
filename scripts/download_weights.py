import os
import sys

import requests


def download_yolov13n(save_dir):
    # 1. 配置模型下载链接和保存路径
    model_name = "yolov13n.pt"
    # YOLOv13n.pt官方直接下载链接（无需GitHub API，稳定性高）
    download_url = "https://github.com/iMoonLab/yolov13/releases/download/yolov13/yolov13n.pt"
    save_path = os.path.join(save_dir, model_name)

    # 2. 确保目标文件夹存在
    os.makedirs(save_dir, exist_ok=True)
    print(f"目标保存路径：{save_path}")

    # 3. 发送请求下载模型（添加超时和用户代理，避免被拦截）
    try:
        print("开始下载 yolov13n.pt...")
        response = requests.get(
            download_url,
            timeout=60,  # 延长超时时间，应对网络较慢情况
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
                "Accept": "application/octet-stream"  # 明确请求二进制文件
            },
            stream=True  # 分块下载，避免内存占用过高
        )
        response.raise_for_status()  # 若状态码非200（如404、403），抛异常提示

        # 4. 分块写入文件（适合大文件，避免内存溢出）
        with open(save_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024 * 1024):  # 1MB/块
                if chunk:
                    f.write(chunk)
                    print(f"已下载：{os.path.getsize(save_path) / (1024 * 1024):.1f}MB", end="\r")

        # 5. 验证下载完整性（yolov13n.pt正常大小约10.6MB）
        final_size = os.path.getsize(save_path) / (1024 * 1024)
        if final_size > 10:  # 若大于10MB，视为下载完整
            print(f"\n✅ 下载成功！模型大小：{final_size:.1f}MB")
            print(f"模型保存路径：{save_path}")
        else:
            os.remove(save_path)  # 删除不完整文件
            print(f"\n❌ 下载失败：文件不完整（仅{final_size:.1f}MB，正常约10.6MB），请重试！")

    except requests.exceptions.Timeout:
        print("\n❌ 下载超时：网络连接过慢，请检查网络后重试！")
    except requests.exceptions.HTTPError as e:
        print(f"\n❌ 下载失败：HTTP错误 {e.response.status_code}，可能是链接失效或网络限制！")
        print("建议手动下载：https://github.com/iMoonLab/yolov13/releases/download/yolov13/yolov13n.pt")
    except Exception as e:
        print(f"\n❌ 下载失败：{str(e)}")


# 调用函数，指定你的目标保存文件夹
if __name__ == "__main__":
    # 默认下载到项目根的 models/ 目录，也可以用第一个命令行参数指定
    target_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")
    download_yolov13n(target_dir)