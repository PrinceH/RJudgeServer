#include<bits/stdc++.h>
using namespace std;

int main(){
	//ios::sync_with_stdio(false);
	double a, ans, temp;
	long long k;
	while(scanf("%lf%lld",&a,&k)){
		ans = 0;
		for(int i = 1; i <= k; i ++){
			ans += a;
			a /= 2;
			if(a < 0.001)break;
			temp = a;
			if(i != k)ans += a;
		}
		printf("%.1f %.1f\n",ans, temp);
	}
    return 0;
}
