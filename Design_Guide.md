🎨 Design Guideline: "Midnight Yacht Club"
1. Color Palette (색상 팔레트)
이미지에서 추출한 핵심 색상은 **'Deep Dark Background'**와 **'Soft Neon Gradients'**입니다. 눈이 편안하면서도 중요한 정보(점수, 주사위)가 돋보여야 합니다.

Background (Base): #1A1A1A (완전한 블랙보다는 짙은 차콜 그레이, 이미지의 배경색)

Surface (Cards/Areas): #252525 (배경보다 아주 조금 밝은 카드 배경)

Text (Primary): #FFFFFF (제목, 내 점수)

Text (Secondary): #A0A0A0 (설명, 상대방 점수, 비활성 텍스트)

Accent (Gradients): 이미지 하단의 게이지 바에서 영감을 얻은 포인트 컬러

Primary Action (Roll 버튼): Blue-Cyan Gradient (#4facfe to #00f2fe)

Highlight (선택된 주사위): Peach-Orange Gradient (#f6d365 to #fda085) - 이미지의 'Leisure Activities' 바 색상 참고

Success/Win: Mint-Green Gradient (#84fab0 to #8fd3f4)

2. Typography (타이포그래피)
이미지의 폰트는 산세리프(Sans-serif) 계열로 가독성이 높고 모던합니다.

Font Family: Montserrat (제목용) + Inter 또는 Open Sans (본문/숫자용)

Style:

점수판의 숫자는 Monospace(고정폭) 폰트를 섞어 쓰거나, font-variant-numeric: tabular-nums; 속성을 주어 숫자가 흔들리지 않고 가지런히 정렬되게 합니다.

제목("Manhattan 96" 처럼)은 얇은 두께(Light/Thin)와 굵은 두께(Bold)를 대비시켜 세련미를 줍니다.

3. Layout & Components (레이아웃 및 구성요소)
A. 글래스모피즘 (Glassmorphism) 카드 디자인 이미지의 흰색 박스(Diesel)나 투명한 영역처럼, 게임의 요소를 반투명한 카드 위에 올립니다.

Scoreboard: 엑셀 표 같은 딱딱한 선 대신, 배경이 살짝 비치는 어두운 패널 위에 점수를 배치합니다.

Border: 카드 테두리에 아주 얇은(1px) #333333 색상을 주어 배경과 은은하게 분리합니다.

B. 주사위 (The Hero Object) 이미지의 '요트'가 주인공이듯, 이 웹사이트의 주인공은 주사위입니다.

Dice Style: 흰색 바탕에 검은 점(기본)보다는, 어두운 반투명 재질의 주사위에 **형광색 점(Pip)**이 빛나는 스타일을 추천합니다.

Animation: 주사위가 굴러갈 때 잔상(Motion Blur) 효과를 주어 스피드감을 살립니다. (Anime.js 활용)

C. 게이지 바 (Gauge Bars) 이미지 우측 하단의 Furnishings, Equipment 바는 게임 UI로 훌륭하게 변환될 수 있습니다.

활용처:

남은 시간 (Turn Timer): 시간이 줄어들수록 바가 줄어드는 애니메이션.

현재 총점 비교: 나와 상대방의 점수 차이를 시각적인 막대그래프로 표현.

4. CSS Strategy (Bootstrap + Custom)
Bootstrap 5를 기반으로 하되, 기본 스타일을 덮어써야 합니다.

CSS

/* Custom CSS Snippet Idea */
body {
    background-color: #1A1A1A;
    color: #ffffff;
    font-family: 'Inter', sans-serif;
}

.game-card {
    background: rgba(37, 37, 37, 0.7); /* 반투명 */
    backdrop-filter: blur(10px);        /* 흐림 효과 */
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 16px;
    box-shadow: 0 4px 30px rgba(0, 0, 0, 0.5);
}

.btn-roll {
    /* 이미지 속 밝은 포인트 컬러 느낌 */
    background: linear-gradient(135deg, #f6d365 0%, #fda085 100%);
    border: none;
    color: #1A1A1A;
    font-weight: 700;
}

.dice-active {
    box-shadow: 0 0 15px rgba(79, 172, 254, 0.6); /* 선택 시 은은한 발광 */
}