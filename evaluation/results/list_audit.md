# 블랙리스트·허용 목록 점검 (2026-10-16)

- 블랙리스트: 주소 35,274건, 호스트 15,868건 (KISA 2024-12-31 기준)
- 허용 목록: 501개 도메인
- 검토된 예외 1건, 검토된 추가 0건

## 1. 공용 주소와 겹치는 블랙리스트 호스트
호스트 단위로 확정하면 그 플랫폼·공식 사이트 전체가 피싱이 되는 항목이다. 서비스는 호스트 단위로 확정하지 않는다.

- `bit.ly`
- `cutt.ly`
- `goo.gl`
- `line.me`
- `m.abc.com`
- `m.site.naver.com`
- `pf.kakao.com`
- `s3-ap-east-1.amazonaws.com`
- `t.me`
- `telegram.org`
- `tinyurl.com`
- `www.nhis.or.kr`

## 2. 경로 없이 들어 있는 공용 주소
사칭 대상(공식 사이트)이나 이메일 주소가 그대로 들어간 경우로 보인다. 서비스는 확정하지 않는다.

- `***@naver.com`
- `tinyurl.com`
- `www.nhis.or.kr`

공용 주소 안의 '경로까지 일치하는' 신고 페이지 785건은 계속 피싱으로 확정한다.

## 3. 단축 URL 호스트
단축 URL은 호스트 단위로 확정하지 않고 '주의'로 표시한다 (shorteners.py).

- `abit.ly`
- `bit.ly`
- `bitly.kr`
- `buly.kr`
- `c11.kr`
- `cutt.ly`
- `gg.gg`
- `goo.gl`
- `han.gl`
- `is.gd`
- `link24.kr`
- `lrl.kr`
- `me2.do`
- `muz.so`
- `naver.me`
- `ow.ly`
- `qrco.de`
- `rb.gy`
- `rebrand.ly`
- `s.id`
- `shorturl.asia`
- `shorturl.at`
- `t.ly`
- `tiny.cc`
- `tinyurl.com`
- `url.kr`
- `v.gd`
- `vo.la`
- `www.buly.kr`
- `www.t.ly`
- `zrr.kr`

## 4. 형식이 깨진 값 (33건, 서비스가 읽을 때 버림)

- `-dokdo.in`
- `....`
- `.com`
- `1522-6582`
- `15225268`
- `1660-0238`
- `18992753`
- `953.456.765`
- `buly.`
- `bx.m2ds`
- `club`
- `han.gl.8jork`
- `han.gl.dzm54`
- `han.glq9k`
- `hhttp:`
- `http:`
- `https:`
- `is.g`
- `k.r`
- `kag.rn7m.`
- `kca`
- `kr.mobile-simple`
- `***@naver.com`
- `lrl.k`
- `mcf`
- `nc.ca3s.art2024`
- `qrco.d`
- `rnddm`
- `secretbox`
- `singlecam`
- `syi.qpji.world=oic`
- `xxx`
- `ylc.et5a.l`
