'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/lib/store';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { CheckCircle2, XCircle, MapPin, Plane, Calendar } from 'lucide-react';

export default function AuthPage() {
  const router = useRouter();
  const { user, isAuthenticated, login } = useAuthStore();

  const [loginData, setLoginData] = useState({ username: '', password: '' });
  const [registerData, setRegisterData] = useState({ username: '', password: '', confirmPassword: '' });
  const [loginErrors, setLoginErrors] = useState<string[]>([]);
  const [registerErrors, setRegisterErrors] = useState<string[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated && user) {
      router.push('/');
    }
  }, [isAuthenticated, user, router]);

  const validateUsername = (username: string): string[] => {
    const errors: string[] = [];
    if (username.length < 6) errors.push('账号至少需要6位字符');
    if (!/^[a-zA-Z0-9]+$/.test(username)) errors.push('账号只能包含英文和数字');
    return errors;
  };

  const validatePassword = (password: string): string[] => {
    const errors: string[] = [];
    if (password.length < 8) errors.push('密码至少需要8位字符');
    if (!/^(?=.*[a-zA-Z])(?=.*\d).+$/.test(password)) errors.push('密码必须包含英文和数字');
    return errors;
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoginErrors([]);

    const usernameErrors = validateUsername(loginData.username);
    const passwordErrors = validatePassword(loginData.password);

    if (usernameErrors.length > 0 || passwordErrors.length > 0) {
      setLoginErrors([...usernameErrors, ...passwordErrors]);
      return;
    }

    setIsSubmitting(true);
    // Simulate login
    setTimeout(() => {
      // Check if user exists in localStorage (simulated)
      const users = JSON.parse(localStorage.getItem('travel-users') || '{}');
      if (users[loginData.username]?.password === loginData.password) {
        login(loginData.username);
        router.push('/');
      } else {
        // For demo, allow any valid format to login
        login(loginData.username);
        router.push('/');
      }
      setIsSubmitting(false);
    }, 500);
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setRegisterErrors([]);

    const usernameErrors = validateUsername(registerData.username);
    const passwordErrors = validatePassword(registerData.password);

    if (usernameErrors.length > 0 || passwordErrors.length > 0) {
      setRegisterErrors([...usernameErrors, ...passwordErrors]);
      return;
    }

    if (registerData.password !== registerData.confirmPassword) {
      setRegisterErrors(['两次输入的密码不一致']);
      return;
    }

    setIsSubmitting(true);
    // Simulate registration
    setTimeout(() => {
      const users = JSON.parse(localStorage.getItem('travel-users') || '{}');
      if (users[registerData.username]) {
        setRegisterErrors(['该账号已被注册']);
        setIsSubmitting(false);
        return;
      }

      users[registerData.username] = { password: registerData.password };
      localStorage.setItem('travel-users', JSON.stringify(users));

      login(registerData.username);
      router.push('/');
      setIsSubmitting(false);
    }, 500);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 via-sky-50/30 to-slate-100 p-4">
      <div className="w-full max-w-md space-y-6">
        {/* Logo and Title */}
        <div className="text-center space-y-2">
          <div className="flex justify-center items-center gap-2 mb-4">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-sky-500 to-teal-500 flex items-center justify-center shadow-lg">
              <MapPin className="w-6 h-6 text-white" />
            </div>
          </div>
          <h1 className="text-2xl font-bold text-slate-800">AI旅行规划工作台</h1>
          <p className="text-slate-500 text-sm">智能规划，畅行无忧</p>
        </div>

        {/* Auth Card */}
        <Card className="border-0 shadow-xl bg-white/80 backdrop-blur">
          <Tabs defaultValue="login" className="w-full">
            <TabsList className="grid w-full grid-cols-2 bg-slate-100/50 m-1">
              <TabsTrigger value="login" className="data-[state=active]:bg-white data-[state=active]:shadow-sm">
                登录
              </TabsTrigger>
              <TabsTrigger value="register" className="data-[state=active]:bg-white data-[state=active]:shadow-sm">
                注册
              </TabsTrigger>
            </TabsList>

            <TabsContent value="login" className="p-6 pt-4 space-y-4">
              <form onSubmit={handleLogin} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="login-username">账号</Label>
                  <Input
                    id="login-username"
                    type="text"
                    placeholder="请输入账号"
                    value={loginData.username}
                    onChange={(e) => setLoginData({ ...loginData, username: e.target.value })}
                    className="bg-white"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="login-password">密码</Label>
                  <Input
                    id="login-password"
                    type="password"
                    placeholder="请输入密码"
                    value={loginData.password}
                    onChange={(e) => setLoginData({ ...loginData, password: e.target.value })}
                    className="bg-white"
                  />
                </div>

                <div className="bg-slate-50 rounded-lg p-3 text-xs text-slate-500 space-y-1">
                  <div className="flex items-center gap-2">
                    <span>账号规则：</span>
                  </div>
                  <div className="flex items-center gap-1.5 ml-2">
                    {loginData.username.length >= 6 ? (
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                    ) : (
                      <XCircle className="w-3.5 h-3.5 text-slate-300" />
                    )}
                    <span>至少6位英文和数字</span>
                  </div>
                  <div className="flex items-center gap-1.5 ml-2">
                    {/^[a-zA-Z0-9]+$/.test(loginData.username) && loginData.username.length > 0 ? (
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                    ) : (
                      <XCircle className="w-3.5 h-3.5 text-slate-300" />
                    )}
                    <span>仅限英文和数字</span>
                  </div>
                </div>

                {loginErrors.length > 0 && (
                  <Alert variant="destructive">
                    <AlertDescription>
                      <ul className="space-y-1">
                        {loginErrors.map((err, i) => (
                          <li key={i}>{err}</li>
                        ))}
                      </ul>
                    </AlertDescription>
                  </Alert>
                )}

                <Button
                  type="submit"
                  className="w-full bg-gradient-to-r from-sky-500 to-teal-500 hover:from-sky-600 hover:to-teal-600"
                  disabled={isSubmitting}
                >
                  {isSubmitting ? '登录中...' : '登录'}
                </Button>
              </form>
            </TabsContent>

            <TabsContent value="register" className="p-6 pt-4 space-y-4">
              <form onSubmit={handleRegister} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="register-username">账号</Label>
                  <Input
                    id="register-username"
                    type="text"
                    placeholder="请设置账号"
                    value={registerData.username}
                    onChange={(e) => setRegisterData({ ...registerData, username: e.target.value })}
                    className="bg-white"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="register-password">密码</Label>
                  <Input
                    id="register-password"
                    type="password"
                    placeholder="请设置密码"
                    value={registerData.password}
                    onChange={(e) => setRegisterData({ ...registerData, password: e.target.value })}
                    className="bg-white"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="register-confirm">确认密码</Label>
                  <Input
                    id="register-confirm"
                    type="password"
                    placeholder="请再次输入密码"
                    value={registerData.confirmPassword}
                    onChange={(e) => setRegisterData({ ...registerData, confirmPassword: e.target.value })}
                    className="bg-white"
                  />
                </div>

                <div className="bg-slate-50 rounded-lg p-3 text-xs text-slate-500 space-y-1">
                  <div className="font-medium text-slate-600 mb-1">账号规则</div>
                  <div className="flex items-center gap-1.5">
                    {registerData.username.length >= 6 ? (
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                    ) : (
                      <XCircle className="w-3.5 h-3.5 text-slate-300" />
                    )}
                    <span>至少6位字符</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    {/^[a-zA-Z0-9]+$/.test(registerData.username) && registerData.username.length > 0 ? (
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                    ) : (
                      <XCircle className="w-3.5 h-3.5 text-slate-300" />
                    )}
                    <span>仅限英文和数字</span>
                  </div>
                  <div className="font-medium text-slate-600 mb-1 mt-2">密码规则</div>
                  <div className="flex items-center gap-1.5">
                    {registerData.password.length >= 8 ? (
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                    ) : (
                      <XCircle className="w-3.5 h-3.5 text-slate-300" />
                    )}
                    <span>至少8位字符</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    {/^(?=.*[a-zA-Z])(?=.*\d).+$/.test(registerData.password) && registerData.password.length > 0 ? (
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                    ) : (
                      <XCircle className="w-3.5 h-3.5 text-slate-300" />
                    )}
                    <span>必须包含英文和数字</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    {registerData.confirmPassword && registerData.password === registerData.confirmPassword ? (
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                    ) : (
                      <XCircle className="w-3.5 h-3.5 text-slate-300" />
                    )}
                    <span>两次密码一致</span>
                  </div>
                </div>

                {registerErrors.length > 0 && (
                  <Alert variant="destructive">
                    <AlertDescription>
                      <ul className="space-y-1">
                        {registerErrors.map((err, i) => (
                          <li key={i}>{err}</li>
                        ))}
                      </ul>
                    </AlertDescription>
                  </Alert>
                )}

                <Button
                  type="submit"
                  className="w-full bg-gradient-to-r from-sky-500 to-teal-500 hover:from-sky-600 hover:to-teal-600"
                  disabled={isSubmitting}
                >
                  {isSubmitting ? '注册中...' : '注册'}
                </Button>
              </form>
            </TabsContent>
          </Tabs>
        </Card>

        {/* Features */}
        <div className="grid grid-cols-3 gap-3 text-center text-xs">
          <div className="flex flex-col items-center gap-1">
            <div className="w-10 h-10 rounded-full bg-sky-100 flex items-center justify-center">
              <Plane className="w-5 h-5 text-sky-600" />
            </div>
            <span className="text-slate-600">智能交通</span>
          </div>
          <div className="flex flex-col items-center gap-1">
            <div className="w-10 h-10 rounded-full bg-teal-100 flex items-center justify-center">
              <Calendar className="w-5 h-5 text-teal-600" />
            </div>
            <span className="text-slate-600">时间规划</span>
          </div>
          <div className="flex flex-col items-center gap-1">
            <div className="w-10 h-10 rounded-full bg-amber-100 flex items-center justify-center">
              <MapPin className="w-5 h-5 text-amber-600" />
            </div>
            <span className="text-slate-600">景点推荐</span>
          </div>
        </div>
      </div>
    </div>
  );
}
