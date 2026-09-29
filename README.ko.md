# WSR_Localisation_kit — Wall Street Raider 다국어 번역 프레임워크

WSR_Localisation_kit은 WSR_KR 한국어 패치에서 출발해, 여러 언어를 같은 방식으로 번역할 수 있도록 확장된 다국어 번역 프레임워크입니다. 메뉴·버튼·설정 같은 고정 UI뿐 아니라 뉴스, 투자 자문 보고서, 리서치 리포트, 실적 보고서처럼 게임이 그때그때 만들어내는 문장까지 번역합니다.

- **한국어**는 완성본이며, 다른 언어 번역의 참고용으로 함께 들어 있습니다.
- **일본어·프랑스어**는 예시로 넣은 것입니다. 내부 테스트는 마쳤지만 번역 칸은 모두 비어 있습니다.

한국어 번역의 특징:

- 회사·산업·국가 이름, 금액, 날짜가 들어간 문장도 자연스럽게 번역하며, 조사(은/는, 이/가 …)를 앞 단어에 맞춰 자동으로 고릅니다.
- 금융 용어와 표 머리글에 설명 툴팁을 달았습니다.
- 한국어 때문에 깨지는 표와 히트맵 레이아웃을 보정했고, 차트의 월 표시를 한국어로 그립니다.

> 게임 실행 파일이나 원본 게임 파일은 배포하지 않습니다. 정품 Wall Street Raider(Steam)가 필요합니다.

## 설치

1. [한국어 패치 v1.0.0 릴리스](https://github.com/NainUrbain/WSR_Localisation_kit/releases/tag/ko-v1.0.0) 페이지에서 `WSR_KR_user.exe`를 받습니다.
2. 게임을 종료하고 `WSR_KR_user.exe`를 실행합니다.
3. 게임 폴더를 자동으로 찾지 못하면 Wall Street Raider 설치 폴더를 지정합니다.
   - 예: `D:\SteamLibrary\steamapps\common\Wall Street Raider`
4. 게임을 실행하고 언어 설정에서 `한국어`를 선택합니다.

설치 파일에 코드 서명이 없어 Windows SmartScreen 경고가 뜨거나 일부 백신이 오진할 수 있습니다. **이 저장소의 Releases에서 받은 파일**이라면 `추가 정보 → 실행`을 누르면 됩니다.

## 패치가 하는 일

패치는 게임 파일 9개를 수정하고, 번역에 필요한 파일을 게임의 `js/` 폴더에 추가합니다. 설치 전에 게임 버전이 맞는지 확인해서, 맞지 않으면 아무것도 건드리지 않고 멈춥니다. 원본은 `wsr-kr-player-backup/` 폴더에 백업합니다.

**게임이 업데이트되면 패치가 망가질 가능성이 매우 높습니다.** 이때는 아래 방법으로 제거한 뒤, 새 버전의 WSR_KR이 나오면 다시 설치하세요.

## 제거

1. Steam에서 Wall Street Raider → 속성 → 설치된 파일 → **게임 파일 무결성 확인**을 실행합니다. 수정된 9개 파일이 원래대로 돌아옵니다.
2. (선택) 패치가 추가한 파일을 지웁니다. 남겨 둬도 게임이 읽지 않으므로 문제는 없습니다.
   - `wsr-kr-player-backup/` 폴더
   - `js/` 폴더: `attachJosa.js`, `dom-translate-hook.js`, `glossary-tooltip.js`, `grammar-select.js`, `lang-*.js`, `locale-registry.js`, `template-apply.js`, `template-translate.js`
   - `js/locale/` 폴더: `header-lines.json`, `wsr-locales.json`, `ko-glossary.json`, `ko-header-glossary.json`, `ko-header-terms.json`, `ko-hook-data.json`, `ko-templates.json`

세이브 파일은 설치나 제거 과정에서 건드리지 않습니다.

## 알려진 한계

- 게임 업데이트 직후에는 대응 버전이 나올 때까지 설치할 수 없습니다.
- 드물게 조합되는 일부 문장은 영어로 남거나 부분적으로만 번역될 수 있습니다.
- 고정폭 보고서와 표의 머리글은 번역문으로 바꾸면 열 정렬이 무너지므로 영어로 유지되며, 번역은 마우스를 올렸을 때 나타나는 툴팁으로 제공합니다.
- 번역 키는 게임 데이터와 직접 상호작용하지 않고, 각 번역 항목이 무엇인지 구분하는 식별용 태그로만 사용됩니다.
- 뉴스 이벤트의 `@HUMOR`, `@TEXTSTRING`처럼 생성 값과 정확한 의미를 안정적으로 파악할 수 없는 토큰이 포함된 문장은 번역용 CSV에 수록하지 않았습니다.
- 창 크기와 글꼴에 따라 긴 표나 버튼 라벨이 줄바꿈될 수 있습니다.

번역 오류나 어색한 문장은 [Issues](../../issues)에 화면 캡처와 함께 남겨 주세요.

## 번역에 참여하거나 다른 언어로 만들고 싶다면

번역 데이터는 CSV 파일이고, 게임 안에서 바로 고쳐 보며 작업할 수 있는 번역자용 키트가 있습니다. 자세한 내용은 영문 [README](README.md)와 [다국어 가이드](wsr_package_build/MULTILINGUAL.md)를 참고하세요.

## 라이선스와 허가

- 코드: [PolyForm Noncommercial 1.0.0](LICENSE). 비상업적 목적이라면 자유롭게 사용·수정·공유할 수 있으며, 저작권 표시(`Required Notice`)를 유지해야 합니다.
- 번역 데이터: [CC BY-NC 4.0](LICENSE-DATA.md). 출처("Nain Urbain 이영찬")를 표기하면 자유롭게 수정·공유할 수 있지만, 상업적으로 이용할 수는 없습니다.
- 코드와 번역 데이터 모두 상업적으로 이용하려면 저작권자에게 별도 허락을 받아야 합니다.

WSR_Localisation_kit은 Wall Street Raider 제작자의 허락을 받아 무료로 배포하는 비공식 번역 프레임워크입니다.
