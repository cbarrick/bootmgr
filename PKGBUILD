pkgname=bootmgr-git
pkgver=1.0.0
pkgrel=1

pkgdesc='A configuration framework for EFI boot entries'
arch=('any')
url='https://github.com/cbarrick/bootmgr'
license=('MIT') # TODO: copy license file to /usr/share/licenses/bootmgr
depends=('efibootmgr' 'python-toml>=0.9.0' 'python>=3.6')
provides=('bootmgr')
conflicts=('bootmgr')

source=('git+https://github.com/cbarrick/bootmgr#branch=master')
md5sums=('SKIP')

pkgver() {
	cd "${srcdir}/bootmgr"
	printf "1.0.0_r%s.%s" \
		$(git rev-list --count HEAD) \
		$(git rev-parse --short HEAD)
}

package() {
	cd "${srcdir}/bootmgr"
	install -Dm644 LICENSE "${pkgdir}/usr/share/licenses/${pkgname}/LICENSE"
	make install DESTDIR="${pkgdir}" PREFIX="/usr"
}
