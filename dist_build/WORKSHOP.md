# Steam Workshop 빌드 및 업로드

WSR의 `workshopLoader.js`와 `workshopProtocol.js`에서 확인한 규격은
`resources/app`와 같은 상대 경로를 갖는 파일 오버레이입니다.
별도의 `mod.json` 진입점은 사용하지 않습니다. 같은 경로를 제공하는 모드는
나중에 로딩된 파일이 우선합니다.

## 빌드

```powershell
.\dist_build\2_build_player_release.bat ko-KR
powershell -NoProfile -ExecutionPolicy Bypass -File dist_build/create_workshop_preview.ps1 -Output dist_build/dist/workshop_ko-KR/preview.png
```

기본 배포 명령은 EXE 대신 워크샵 폴더를 출력합니다. Python 3.10 이상이 필요하며
PyInstaller는 필요하지 않습니다. 게임 경로를 생략하면 설치본을 자동 탐색합니다.
직접 지정하려면 두 번째 인수에 게임 경로, 세 번째 인수에 새 출력 폴더를 넣습니다.
번역 키트에서는 `build_player.bat ko-KR`로 같은 작업을 수행합니다.

출력: `dist_build/dist/workshop_ko-KR/` (번역 키트는 `dist/workshop_ko-KR/`).
이미 존재하면 세 번째 인수에 새 폴더를 지정합니다. Python 빌더를 직접 사용할 때는
`--output`을 지정하며, `--locale`로 언어를 선택할 수 있습니다.
기존 게시물 ID가 저장된 폴더를 실수로 덮어쓰지 않도록 자동 삭제하지 않습니다.

빌더는 게임 설치 폴더를 수정하지 않습니다. 지원 원본의 SHA-256을 검사하고,
이미 패치된 설치에서는 해시가 일치하는 기존 백업을 사용합니다. 원본 9개에
플레이어 패치를 적용한 복사본과 한국어 런타임을 `content/js/`에 만듭니다.
JSON 데이터는 JS 모듈에도 묶어 디스크 직접 읽기 대신 워크샵 로더를 통해
읽습니다. 따라서 설치 폴더에 번역 JSON이 없어도 적용됩니다.

생성된 게임 UI 파일은 원 저작권자의 권리를 유지하며 Git에 넣지 않습니다.
기존 설치형 배포와 달리 워크샵 업로드에는 수정된 게임 UI 파일 9개가 포함됩니다.
코드/번역 라이선스가 게임 코드까지 재라이선스하는 것은 아닙니다.

자동 검증 (실제 설치 파일은 수정하지 않고 임시 폴더에서 모드 로딩을 검사):

```powershell
node --experimental-vm-modules wsr_package_build/tests/workshop.test.cjs dist_build/dist/workshop_ko-KR "E:\SteamLibrary\steamapps\common\Wall Street Raider\resources\app"
```

게임 모듈 연결, 디스크 JSON 없이 한국어 번역 데이터 로딩, 실제 워크샵 로더와
프로토콜, 구독 해제 동작을 검사합니다. 실제 Steam 다운로드와 화면 QA는 별도입니다.

## 업로더 입력

게임에 포함된 `mod-uploader/wsr-mod-uploader.exe`를 사용합니다.

- Mod folder: 출력 안의 **`content` 폴더** (상위 폴더나 ZIP 아님)
- Title: `WSR Korean Localization — 한국어 번역`
- Description: `description.ko.txt` 내용
- Tags: `Locale`, 필요하면 `UI Extension`
- Preview: 1 MB 미만 PNG/JPG (출력 폴더의 `preview.png` 사용 가능)
- Visibility: 첫 확인은 Private 권장. 실제 게임 확인 후 Public으로 전환

업로더가 만든 `.wsrmod-id`는 기존 게시물 업데이트에 쓰이므로 보관합니다.
다음 빌드의 content 파일을 기존 업로드 폴더로 갱신할 때 ID를 삭제하지 마세요.
`build-report.json`은 로컬 경로와 검증 정보를 담으므로 업로드 대상이 아닙니다.

## 구독 적용과 확인

구독한 뒤 게임을 완전히 종료하고 다시 실행하여 언어 설정에서 한국어를 선택합니다.
별도 EXE/Python 설치는 필요하지 않습니다. 구독 해제 후 재실행하면 오버레이가
해제됩니다. 기존 수동 패치는 별개이므로 수동 패치를 제거한 정상 게임에서 확인합니다.

메뉴, 뉴스/동적 보고서, 용어/표 머리글 툴팁, 차트 월 표시, 영어 전환을 확인하세요.
게임 업데이트나 동일한 `js/api.js`, `js/app.js`, `js/locale/localeManager.js`,
`js/components/` 파일을 바꾸는 다른 모드와의 충돌 가능성이 있습니다.
해시 검사는 빌드 시 수행하며 워크샵 로더 자체는 게임 업데이트 호환성을 검사하지 않습니다.
