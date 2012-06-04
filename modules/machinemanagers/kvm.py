# Copyright (C) 2010-2012 Cuckoo Sandbox Developers.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

from lib.cuckoo.common.abstracts import MachineManager
from lib.cuckoo.common.exceptions import CuckooDependencyError, CuckooMachineError

try:
    import libvirt
except ImportError:
    raise CuckooDependencyError("Unable to import libvirt")


class Kvm(MachineManager):
    """Virtualization layer for KVM based on python-libvirt."""

    def start(self, label):
        """Start a virtual machine.
        @param label: virtual machine name.
        @raise CuckooMachineError: if unable to start virtual machine.
        """
        # Connect.
        self._connect()
        # Search.
        vm = self._lookup(label)
        # Get current snapshot.
        try:
            snap = vm.hasCurrentSnapshot(flags=0)
        except libvirt.libvirtError:
            raise CuckooMachineError("Unable to get current snapshots for virtual machine %s" % label)
        # Revert to latest snapshot.
        if snap:
            try:
                vm.revertToSnapshot(vm.snapshotCurrent(flags=0), flags=0)
            except libvirt.libvirtError:
                raise CuckooMachineError("Unable to restore snapshot on virtual machine %s" % label)
        else:
            raise CuckooMachineError("No snapshots found for virtual machine %s" % label)

    def stop(self, label):
        """Stops a virtual machine. Kill them all.
        @param label: virtual machine name.
        @raise CuckooMachineError: if unable to stop virtual machine.
        """
        # Connect.
        self._connect()
        # Search.
        vm = self._lookup(label)
        # Force virtual machine shutdown (hardcore way).
        try:
            vm.destroy()
        except libvirt.libvirtError:
            raise CuckooMachineError("Error stopping virtual machine %s" % label)

    def _connect(self):
        """Connects to libvirt subsystem.
        @raise CuckooMachineError: if cannot connect to libvirt.
        """
        try:
            self.conn = libvirt.open("qemu:///system")
        except libvirt.libvirtError:
            raise CuckooMachineError("Cannot connect to libvirt")

    def _lookup(self, label):
        """Search for a virtual machine.
        @param label: virtual machine name.
        @raise CuckooMachineError: if virtual machine is not found.
        """
        try:
            vm = self.conn.lookupByName(label)
        except libvirt.libvirtError:
                raise CuckooMachineError("Cannot found machine %s" % label)
        return vm

    def _list(self):
        """List available virtual machines.
        @raise CuckooMachineError: if unable to list virtual machines.
        """
        try:
            names = self.conn.listDefinedDomains()
        except libvirt.libvirtError:
            raise CuckooMachineError("Cannot list domains")
        return names

    def _version_check(self):
        """Check if libvirt release supports snapshots.
        @return: True or false.
        """
        if libvirt.getVersion() >= 8000:
            return True
        else:
            return False
