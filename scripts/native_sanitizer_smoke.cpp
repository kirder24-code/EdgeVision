#include <cassert>
#include <cmath>
#include <iostream>
extern "C" {
struct EVDetection {double x,y,w,h;};
struct EVTrack {int id; double x,y,w,h; int missed;};
void* ev_tracker_create(double, int);
void ev_tracker_destroy(void*);
int ev_tracker_update(void*, const EVDetection*, int, EVTrack*, int);
}
int main() {
    void* t = ev_tracker_create(65, 2);
    assert(t);
    EVTrack result[8]{};
    EVDetection a[]{{10,20,10,10},{110,40,10,10}};
    assert(ev_tracker_update(t,a,2,result,8)==2);
    const int aid=result[0].id, bid=result[1].id;
    assert(aid!=bid);
    EVDetection bad[]{{NAN,20,10,10}};
    assert(ev_tracker_update(t,bad,1,result,8)==-2);
    assert(ev_tracker_update(t,a,2,result,1)==-3);
    for(int i=1;i<=3;i++) {
        EVDetection moving[]{{10+i*12.,20,10,10},{110-i*12.,40,10,10}};
        assert(ev_tracker_update(t,moving,2,result,8)==2);
        assert(result[0].id==aid && result[1].id==bid);
    }
    assert(ev_tracker_update(t,nullptr,0,result,8)==2);
    assert(ev_tracker_update(t,nullptr,0,result,8)==2);
    assert(ev_tracker_update(t,nullptr,0,result,8)==0);
    ev_tracker_destroy(t);
    std::cout << "native ABI smoke passed" << std::endl;
}
