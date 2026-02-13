#!/usr/bin/env python3
"""
RSS 日报生成器 - 获取 Andrej Karpathy 精选 RSS 内容并生成飞书文档
"""

import os
import sys
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import feedparser
import requests
from readability import Document


class RSSItem:
    """RSS 条目"""
    def __init__(self, title: str, link: str, published: datetime, source: str, summary: str = ""):
        self.title = title
        self.link = link
        self.published = published
        self.source = source
        self.summary = summary
        self.content = ""

    def __repr__():
        return f"<RSSItem: {self.title[:50]}...>"


class RSSParser:
    """RSS 解析器"""

    def __init__(self, rss_pack_url: str):
        self.rss_pack_url = rss_pack_url
        self.items_24h: List[RSSItem] = []

    def fetch_rss_pack(self) -> List[str]:
        """获取 RSS pack 中的所有 RSS 链接"""
        print(f"📡 正在获取 RSS Pack: {self.rss_pack_url}")

        try:
            response = requests.get(self.rss_pack_url, timeout=30)
            response.raise_for_status()

            # 解析 RSS pack
            feed = feedparser.parse(response.content)

            if feed.bozo and feed.bozo_exception:
                print(f"⚠️  RSS Pack 解析警告: {feed.bozo_exception}")

            # 提取所有 RSS 链接
            rss_links = []
            for entry in feed.entries:
                if 'link' in entry:
                    rss_links.append(entry.link)
                elif 'href' in entry:
                    rss_links.append(entry.href)

            print(f"✅ 找到 {len(rss_links)} 个 RSS 源")
            return rss_links

        except Exception as e:
            print(f"❌ 获取 RSS Pack 失败: {e}")
            return []

    def fetch_feed_items(self, rss_url: str) -> List[RSSItem]:
        """获取单个 RSS feed 的条目"""
        try:
            print(f"  📰 正在获取: {rss_url}")
            response = requests.get(rss_url, timeout=30)
            response.raise_for_status()

            feed = feedparser.parse(response.content)
            items = []

            # 计算 24 小时前的时间
            time_24h_ago = datetime.now() - timedelta(hours=24)

            for entry in feed.entries:
                # 解析发布时间
                published = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    published = datetime(*entry.published_parsed[:6])
                elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                    published = datetime(*entry.updated_parsed[:6])
                else:
                    # 如果没有时间，默认为当前时间
                    published = datetime.now()

                # 只保留过去 24 小时的内容
                if published >= time_24h_ago:
                    title = entry.get('title', '无标题')
                    link = entry.get('link', '')
                    summary = entry.get('summary', entry.get('description', ''))

                    # 获取源名称
                    source = feed.feed.get('title', rss_url)

                    item = RSSItem(title, link, published, source, summary)
                    items.append(item)

            print(f"     找到 {len(items)} 条过去 24h 的更新")
            return items

        except Exception as e:
            print(f"  ⚠️  获取 RSS 失败 ({rss_url}): {e}")
            return []

    def fetch_all_feeds(self) -> List[RSSItem]:
        """获取所有 RSS feed 的条目"""
        rss_links = self.fetch_rss_pack()

        if not rss_links:
            print("❌ 没有找到任何 RSS 链接")
            return []

        all_items = []
        for rss_url in rss_links:
            items = self.fetch_feed_items(rss_url)
            all_items.extend(items)
            time.sleep(0.5)  # 避免请求过快

        # 按时间排序（最新的在前）
        all_items.sort(key=lambda x: x.published, reverse=True)

        print(f"\n✅ 总共找到 {len(all_items)} 条过去 24h 的更新")
        self.items_24h = all_items
        return all_items


class ContentFetcher:
    """内容抓取器"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; RSSDailyBot/1.0)'
        })

    def fetch_article_content(self, url: str) -> str:
        """抓取文章正文内容"""
        try:
            print(f"  📖 正在抓取: {url[:80]}...")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            # 使用 readability 提取正文
            doc = Document(response.content)
            content = doc.summary()

            # 清理 HTML 标签，只保留文本
            import re
            content = re.sub(r'<[^>]+>', '', content)
            content = re.sub(r'\s+', ' ', content)

            # 截取前 500 字符作为摘要
            if len(content) > 500:
                content = content[:500] + "..."

            return content

        except Exception as e:
            print(f"  ⚠️  抓取失败: {e}")
            return ""


class FeishuClient:
    """飞书 API 客户端"""

    def __init__(self, app_id: str, app_secret: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self.base_url = "https://open.feishu.cn/open-apis"
        self.access_token = None
        self.tenant_access_token = None

    def get_tenant_access_token(self) -> bool:
        """获取 tenant_access_token"""
        url = f"{self.base_url}/auth/v3/tenant_access_token/internal"
        data = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }

        try:
            response = requests.post(url, json=data, timeout=10)
            response.raise_for_status()
            result = response.json()

            if result.get('code') == 0:
                self.tenant_access_token = result.get('tenant_access_token')
                print(f"✅ 获取飞书访问令牌成功")
                return True
            else:
                print(f"❌ 获取令牌失败: {result.get('msg')}")
                return False

        except Exception as e:
            print(f"❌ 获取令牌异常: {e}")
            return False

    def create_wiki_space(self, name: str) -> Optional[str]:
        """创建知识库空间"""
        if not self.tenant_access_token:
            return None

        url = f"{self.base_url}/wiki/v2/spaces"
        headers = {
            "Authorization": f"Bearer {self.tenant_access_token}",
            "Content-Type": "application/json"
        }
        data = {
            "name": name,
            "description": "RSS 日报自动生成"
        }

        try:
            response = requests.post(url, json=data, headers=headers, timeout=10)
            result = response.json()

            if result.get('code') == 0:
                space_id = result['data']['space']['space_id']
                print(f"✅ 创建知识库成功: {space_id}")
                return space_id
            else:
                print(f"⚠️  创建知识库失败: {result.get('msg')}")
                return None

        except Exception as e:
            print(f"❌ 创建知识库异常: {e}")
            return None

    def create_document(self, title: str, content: str, folder_token: str = None) -> Optional[str]:
        """创建文档"""
        if not self.tenant_access_token:
            return None

        url = f"{self.base_url}/docx/v1/documents"
        headers = {
            "Authorization": f"Bearer {self.tenant_access_token}",
            "Content-Type": "application/json"
        }
        data = {
            "title": title,
            "folder_token": folder_token
        }

        try:
            response = requests.post(url, json=data, headers=headers, timeout=10)
            result = response.json()

            if result.get('code') == 0:
                doc_id = result['data']['document']['document_id']
                print(f"✅ 创建文档成功: {doc_id}")

                # 添加内容
                self._add_document_content(doc_id, content)

                return doc_id
            else:
                print(f"⚠️  创建文档失败: {result.get('msg')}")
                return None

        except Exception as e:
            print(f"❌ 创建文档异常: {e}")
            return None

    def _add_document_content(self, doc_id: str, content: str):
        """向文档添加内容"""
        url = f"{self.base_url}/docx/v1/documents/{doc_id}/blocks/{doc_id}/children"
        headers = {
            "Authorization": f"Bearer {self.tenant_access_token}",
            "Content-Type": "application/json"
        }

        # 将 Markdown 内容转换为飞书文档块
        blocks = self._markdown_to_blocks(content)

        data = {
            "children": blocks,
            "index": 0
        }

        try:
            response = requests.post(url, json=data, headers=headers, timeout=10)
            result = response.json()

            if result.get('code') == 0:
                print(f"✅ 文档内容添加成功")
            else:
                print(f"⚠️  添加内容失败: {result.get('msg')}")

        except Exception as e:
            print(f"❌ 添加内容异常: {e}")

    def _markdown_to_blocks(self, markdown: str) -> List[Dict]:
        """将 Markdown 转换为飞书文档块（简化版）"""
        blocks = []
        lines = markdown.split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 标题
            if line.startswith('## '):
                blocks.append({
                    "block_type": 4,  # heading2
                    "heading2": {
                        "elements": [{"text_run": {"content": line[3:]}}]
                    }
                })
            elif line.startswith('### '):
                blocks.append({
                    "block_type": 5,  # heading3
                    "heading3": {
                        "elements": [{"text_run": {"content": line[4:]}}]
                    }
                })
            elif line.startswith('> '):
                # 引用块
                blocks.append({
                    "block_type": 12,  # quote
                    "quote": {
                        "elements": [{"text_run": {"content": line[2:]}}]
                    }
                })
            elif line.startswith('- '):
                # 无序列表
                blocks.append({
                    "block_type": 8,  # bullet
                    "bullet": {
                        "elements": [{"text_run": {"content": line[2:]}}]
                    }
                })
            elif line.startswith('---'):
                # 分割线
                blocks.append({
                    "block_type": 14  # divider
                })
            else:
                # 普通文本
                blocks.append({
                    "block_type": 2,  # text
                    "text": {
                        "elements": [{"text_run": {"content": line}}]
                    }
                })

        return blocks


class ReportGenerator:
    """日报生成器"""

    def __init__(self, items: List[RSSItem], content_fetcher: ContentFetcher):
        self.items = items
        self.content_fetcher = content_fetcher
        self.selected_items: List[Tuple[RSSItem, str]] = []  # (item, fetched_content)

    def select_top_items(self, max_per_source: int = 2) -> List[Tuple[RSSItem, str]]:
        """从每个信源选择 top 条目并抓取内容"""
        print(f"\n🔍 正在从每个信源精选 {max_per_source} 条内容...")

        # 按信源分组
        source_items: Dict[str, List[RSSItem]] = {}
        for item in self.items:
            if item.source not in source_items:
                source_items[item.source] = []
            source_items[item.source].append(item)

        # 从每个信源选择前 N 条
        selected = []
        for source, items in source_items.items():
            top_items = items[:max_per_source]
            for item in top_items:
                # 抓取文章内容
                content = self.content_fetcher.fetch_article_content(item.link)
                selected.append((item, content))
                time.sleep(1)  # 避免请求过快

        print(f"✅ 精选了 {len(selected)} 条内容")
        self.selected_items = selected
        return selected

    def generate_report(self) -> str:
        """生成 Markdown 格式的日报"""
        if not self.selected_items:
            print("⚠️  没有可用的内容生成日报")
            return ""

        today = datetime.now().strftime("%Y-%m-%d")
        total_items = len(self.selected_items)
        sources = len(set(item.source for item, _ in self.selected_items))

        # 统计主题（简化版：从标题提取关键词）
        topics = self._extract_topics()

        report = f"""> Andrej Karpathy 精选的信源资讯汇总 | 共 {total_items} 条更新

---

## 🔥 核心主题

{self._format_topics(topics)}

---

"""

        # 按信源分组展示
        source_groups: Dict[str, List[Tuple[RSSItem, str]]] = {}
        for item, content in self.selected_items:
            if item.source not in source_groups:
                source_groups[item.source] = []
            source_groups[item.source].append((item, content))

        emoji_list = ["📖", "💡", "🚀", "🎯", "⚡", "🔮", "🔬", "🎨"]

        for idx, (source, items) in enumerate(source_groups.items()):
            emoji = emoji_list[idx % len(emoji_list)]
            report += f"## {emoji} {source}\n\n"

            for item, content in items:
                report += f"### [{item.title}]({item.link})\n\n"
                if content:
                    report += f"{content}\n\n"
                elif item.summary:
                    # 如果抓取失败，使用 RSS 中的 summary
                    summary = item.summary[:300] + "..." if len(item.summary) > 300 else item.summary
                    report += f"{summary}\n\n"
                report += f"*来源: {item.source} | {item.published.strftime('%Y-%m-%d %H:%M')}*\n\n"
                report += "---\n\n"

        report += f"""
## 📊 今日数据

- **{total_items}** 条 RSS 更新
- **{total_items}** 篇精选深度阅读
- **{sources}** 个信息源
- **{len(topics)}** 个核心主题

## 💡 编者观察

---

*本日报由 AI 自动生成 | 数据源：[Andrej Karpathy curated RSS](https://youmind.com/rss/pack/andrej-karpathy-curated-rss)*
"""

        return report

    def _extract_topics(self) -> List[str]:
        """从标题中提取主题（简化版）"""
        # 简单的关键词提取
        keywords = {}
        for item, _ in self.selected_items:
            # 从标题中提取单词（简化版）
            words = item.title.lower().split()
            for word in words:
                if len(word) > 4:  # 过滤短词
                    keywords[word] = keywords.get(word, 0) + 1

        # 返回出现频率最高的 5 个关键词
        sorted_keywords = sorted(keywords.items(), key=lambda x: x[1], reverse=True)
        return [word for word, count in sorted_keywords[:5]]

    def _format_topics(self, topics: List[str]) -> str:
        """格式化主题列表"""
        if not topics:
            return "暂无明显主题"

        return "、".join([f"**{topic}**" for topic in topics])


def main():
    """主函数"""
    try:
        print("=" * 60)
        print("📰 RSS 日报生成器 - Andrej Karpathy 精选")
        print("=" * 60)

        # 从环境变量获取配置
        feishu_app_id = os.getenv('FEISHU_APP_ID')
        feishu_app_secret = os.getenv('FEISHU_APP_SECRET')
        rss_pack_url = os.getenv('RSS_PACK_URL', 'https://youmind.com/rss/pack/andrej-karpathy-curated-rss')

        print(f"\n🔍 环境检查:")
        print(f"  - FEISHU_APP_ID: {'已设置' if feishu_app_id else '未设置'}")
        print(f"  - FEISHU_APP_SECRET: {'已设置' if feishu_app_secret else '未设置'}")
        print(f"  - RSS_PACK_URL: {rss_pack_url}")

        if not feishu_app_id or not feishu_app_secret:
            print("\n❌ 错误: 缺少飞书 API 凭证")
            print("请设置环境变量: FEISHU_APP_ID 和 FEISHU_APP_SECRET")
            sys.exit(1)

    # 1. 获取 RSS 内容
    print("\n📡 步骤 1: 获取 RSS 内容")
    parser = RSSParser(rss_pack_url)
    items = parser.fetch_all_feeds()

    if not items:
        print("⚠️  过去 24 小时没有新的 RSS 更新")
        sys.exit(0)

    # 2. 抓取文章内容
    print("\n📖 步骤 2: 抓取文章内容")
    fetcher = ContentFetcher()
    generator = ReportGenerator(items, fetcher)
    generator.select_top_items(max_per_source=2)

    # 3. 生成日报
    print("\n📝 步骤 3: 生成日报")
    report = generator.generate_report()

    if not report:
        print("❌ 生成日报失败")
        sys.exit(1)

    # 保存到本地文件（用于调试）
    today = datetime.now().strftime("%Y-%m-%d")
    filename = f"/tmp/rss_report_{today}.md"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"✅ 日报已保存到: {filename}")

    # 4. 发布到飞书
    print("\n🚀 步骤 4: 发布到飞书")
    feishu = FeishuClient(feishu_app_id, feishu_app_secret)

    if feishu.get_tenant_access_token():
        # 创建文档
        doc_title = f"{today} - Karpathy 精选 RSS 日报"
        doc_id = feishu.create_document(doc_title, report)

        if doc_id:
            print(f"🎉 成功！日报已发布到飞书")
            print(f"📄 文档 ID: {doc_id}")
        else:
            print("⚠️  发布到飞书失败，但日报已生成本地文件")
    else:
        print("⚠️  飞书认证失败，日报已生成本地文件")

        print("\n" + "=" * 60)
        print("✅ 任务完成")
        print("=" * 60)

    except Exception as e:
        print("\n" + "=" * 60)
        print("❌ 任务失败")
        print("=" * 60)
        print(f"\n错误类型: {type(e).__name__}")
        print(f"错误信息: {str(e)}")
        print("\n完整堆栈跟踪:")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
