// SPDX-License-Identifier: Apache-2.0
#include <sys/mman.h>
#include <unistd.h>
#include <future>
#include <memory>
#include <thread>
#include <cassert>
#include <dirent.h>
#include <cstdio>
namespace connection_manager {void dump(int fd){char buffer[4096]={0};for(int i=0;i<256;i++)assert(write(fd,buffer,sizeof(buffer))==sizeof(buffer));}}
struct ConnectionDump {
  explicit ConnectionDump(int descriptor) : fd(descriptor) {}
  ~ConnectionDump() { close(fd); }
  const int fd;
  std::promise<void> completed;
};

static void dump_connections_on_main(std::shared_ptr<ConnectionDump> snapshot) {
  // Never write a potentially blocked dumpsys pipe on the Bluetooth main thread.
  connection_manager::dump(snapshot->fd);
  snapshot->completed.set_value();
}

int fds(){DIR* d=opendir("/proc/self/fd");assert(d);int n=0;while(readdir(d))n++;closedir(d);return n;}
int main(){int before=fds();{
 auto s=std::make_shared<ConnectionDump>(memfd_create("test",MFD_CLOEXEC));assert(s->fd>=0);auto future=s->completed.get_future();std::thread mainThread([s]{dump_connections_on_main(s);});
 assert(future.wait_for(std::chrono::seconds(1))==std::future_status::ready);assert(lseek(s->fd,0,SEEK_END)==1048576);mainThread.join();
 }assert(fds()==before);
 {auto s=std::make_shared<ConnectionDump>(memfd_create("timeout",MFD_CLOEXEC));auto future=s->completed.get_future();std::thread late([s]{std::this_thread::sleep_for(std::chrono::milliseconds(30));dump_connections_on_main(s);});assert(future.wait_for(std::chrono::milliseconds(1))==std::future_status::timeout);s.reset();late.join();}
 assert(fds()==before);puts("PASS: 1MiB snapshot finishes without a pipe reader; timed-out callback retains and releases FD");}
