import os
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from pathlib import Path
from string import Template


class SanMiTheater:
    """
    三米影视（www.lyzhibang.com）桌面端
    功能：搜索、生成M3U8播放列表
    """

    def __init__(self):
        self.s = requests.session()
        self.s.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
            "Host": "www.lyzhibang.com",
        }
        # 网址参数
        self.base_url = "https://www.lyzhibang.com/index.php"
        self.search_url = urljoin(self.base_url, "index.php")
        self.onlinePlayer = "https://tools.liumingye.cn/m3u8/#"
        # 首次访问
        self.s.get(self.base_url)
        return

    def search(self, keyword: str) -> list:
        """
        视频搜索功能
        :param keyword: 搜索关键词
        :return: 搜索得到的结果
        """
        search_param = {
            "s": "/home/search/vod",
            "limit": 20,
            "q": keyword,
        }
        search_result = self.s.get(self.search_url, params=search_param).json()["data"]
        return search_result

    @staticmethod
    def show_search(search_result: list) -> None:
        for index, item in enumerate(search_result):
            print(index + 1, item["vod_name"], item["vod_title"], item["vod_url"])
        return

    def vod_chosen(self, search_result: list, index: int) -> dict:
        """
        获取指定剧的播放列表信息
        :param search_result: 根据名称搜索到的剧列表
        :param index: 所选剧编号(1-based)
        :return: 选中剧的播放列表
        """
        # 根据搜索结果选择作品
        chosen_vod = search_result[index - 1]
        vod_url = chosen_vod["vod_url"]
        detail_url = urljoin(self.base_url, vod_url)
        # 获取播放列表
        soup = BeautifulSoup(self.s.get(detail_url).text, features="lxml")
        playlist_soup = soup.find("ul", id="con_playlist_1")
        # 解决反向排序问题
        playlist_reverse = playlist_soup.contents[::-1]
        playlist_dict = {}
        for index, item in enumerate(playlist_reverse):
            playlist_dict[index + 1] = {"episode": item.text, "url": item.a.get("href")}
        return playlist_dict

    @staticmethod
    def vod_name(search_result: list, index: int) -> str:
        chosen_vod = search_result[index - 1]
        vod_name = chosen_vod["vod_name"]
        vod_title = chosen_vod["vod_title"]
        vod_name_detail = f"{vod_name}({vod_title})"
        return vod_name_detail

    def episode_chosen(self, playlist_dict: dict, index: int) -> str:
        """
        获取所选剧特定集数的播放信息
        :param playlist_dict: 所选剧的播放列表
        :param index: 所选集数的编号(1-based)
        :return: 选中集的播放链接
        """
        chosen_episode = playlist_dict[index]
        episode_url = urljoin(self.base_url, chosen_episode["url"])
        episode_soup = BeautifulSoup(self.s.get(episode_url).text, features="lxml")
        script = episode_soup.find("div", id="zanpiancms_player").find("script")
        # regexp = re.compile(r'\{"url":"(https?://(?:[-\w.]|/)+)')
        regexp = re.compile("https:\/\/[a-zA-Z0-9\/\._-]+\.m3u8")
        episode_m3u8 = regexp.findall(script.string)[0]
        return episode_m3u8

    def make_dlp(self, playlist_dict: dict, vod_name: str) -> None:
        """
        制作PotPlayer播放列表
        :param playlist_dict:所选剧的播放列表
        :param vod_name:所选剧的详细名称
        :return:
        """
        episode_template = """
        $index*file*$episode_url
        $index*title*$episode_title"""
        playlist = Template(episode_template)

        dlp_template = """DAUMPLAYLIST
        topindex=0
        saveplaypos=1$playlist"""
        dlp = Template(dlp_template)

        episode_content = []
        for index, item in playlist_dict.items():
            episode_url = self.episode_chosen(playlist_dict, index)
            episode_info = {
                "index": index,
                "episode_url": episode_url,
                "episode_title": item["episode"],
            }
            episode_content.append(playlist.substitute(episode_info))
        dlp_content = dlp.substitute({"playlist": "".join(episode_content)})

        with open(f"{vod_name}.dpl", "w", encoding="utf-8") as f:
            f.write(dlp_content)
        return

    def make_m3u8(self, playlist_dict: dict, vod_name: str) -> Path:
        """
        制作M3U8格式播放列表
        :param playlist_dict:所选剧的播放列表
        :param vod_name:所选剧的详细名称
        :return:m3u8的路径
        """
        episode_template = """#EXTINF:-1,$episode_title\n$episode_url\n"""
        playlist = Template(episode_template)

        m3u8_template = """#EXTM3U\n$playlist"""
        m3u8 = Template(m3u8_template)

        episode_content = []
        for index, item in playlist_dict.items():
            episode_url = self.episode_chosen(playlist_dict, index)
            episode_info = {
                "episode_url": episode_url,
                "episode_title": item["episode"],
            }
            episode_content.append(playlist.substitute(episode_info))
        m3u8_content = m3u8.substitute({"playlist": "".join(episode_content)})
        with open(f"{vod_name}.m3u8", "w", encoding="utf-8") as f:
            f.write(m3u8_content)
        path = f"{vod_name}.m3u8"
        return path

    def play(self, path: Path) -> None:
        """
        调用默认程序打开播放列表
         :param path:视频文件的路径(单个文件：网络路径|多个文件：本地播放列表)
         :return:
        """
        os.startfile(path)
        return

    def online_play(self, path: Path) -> None:
        # TODO 在线播放地址 需用浏览器打开
        onlinePlay_url = f"{self.onlinePlayer}https://cdn6.yzzy-online.com/20221008/19041_7b14eca0/index.m3u8"

    def run(self):
        keyword = input("请输入关键词搜索： ")
        search_result = self.search(keyword)
        self.show_search(search_result)
        vod_index = int(input("请输入剧集序号：")) or 1
        playlist_dict = self.vod_chosen(search_result, vod_index)
        vod_name = self.vod_name(search_result, vod_index)
        path = self.make_m3u8(playlist_dict, vod_name)
        self.play(path)


if __name__ == "__main__":
    san = SanMiTheater()
    san.run()
