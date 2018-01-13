pkgname=bootmgr
pkgver=1.0.0_dev
pkgrel=1

pkgdesc='A configuration framework for EFI boot entries'
arch=('any')
url='https://github.com/cbarrick/bootmgr'
license=('MIT') # TODO: copy license file to /usr/share/licenses/bootmgr
depends=('efibootmgr' 'python-toml>=0.9.0' 'python>=3.6')

source=('https://github.com/cbarrick/bootmgr/archive/master.zip')

package() {
	make DESTDIR="$pkgdir/" install
}
