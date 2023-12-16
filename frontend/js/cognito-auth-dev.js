/*global WildRydes _config AmazonCognitoIdentity AWSCognito*/

var WildRydes = window.WildRydes || {};

(function scopeWrapper($) {
    var signinUrl = '/signin.html';

    var poolData = {
        UserPoolId: _config.cognito.userPoolId,
        ClientId: _config.cognito.userPoolClientId
    };

    var userPool;

    if (!(_config.cognito.userPoolId &&
          _config.cognito.userPoolClientId &&
          _config.cognito.region)) {
        $('#noCognitoMessage').show();
        return;
    }

    userPool = new AmazonCognitoIdentity.CognitoUserPool(poolData);

    if (typeof AWSCognito !== 'undefined') {
        AWSCognito.config.region = _config.cognito.region;
    }

    WildRydes.signOut = function signOut() {
        userPool.getCurrentUser().signOut();
    };

    WildRydes.authToken = new Promise(function fetchCurrentAuthToken(resolve, reject) {
        var cognitoUser = userPool.getCurrentUser();

        if (cognitoUser) {
            cognitoUser.getSession(function sessionCallback(err, session) {
                if (err) {
                    reject(err);
                } else if (!session.isValid()) {
                    resolve(null);
                } else {
                    resolve(session.getIdToken().getJwtToken());
                }
            });
        } else {
            resolve(null);
        }
    });


    /*
     * Cognito User Pool functions
     */

    function register(email, password, onSuccess, onFailure) {
        var dataEmail = {
            Name: 'email',
            Value: email
        };
        console.log(dataEmail);
        var attributeEmail = new AmazonCognitoIdentity.CognitoUserAttribute(dataEmail);

        userPool.signUp(toUsername(email), password, [attributeEmail], null,
            function signUpCallback(err, result) {
                if (!err) {
                    onSuccess(result);
                } else {
                    onFailure(err);
                }
            }
        );
    }


    
    var cognitoUser = new AmazonCognitoIdentity.CognitoUser(userData);

    function signin(email, password, onSuccess, onFailure) {
        var authenticationDetails = new AmazonCognitoIdentity.AuthenticationDetails({
            Username: toUsername(email),
            Password: password,
        });

        var cognitoUser = createCognitoUser(email);
        cognitoUser.authenticateUser(authenticationDetails, {
            onSuccess: onSuccess,
            onFailure: onFailure
        });
    }

    function verify(email, code, onSuccess, onFailure) {
        createCognitoUser(email).confirmRegistration(code, true, function confirmCallback(err, result) {
            if (!err) {
                onSuccess(result);
            } else {
                onFailure(err);
            }
        });
    }

    function createCognitoUser(email) {
        return new AmazonCognitoIdentity.CognitoUser({
            Username: toUsername(email),
            Pool: userPool
        });
    }

    function toUsername(email) {
        return email.replace('@', '-at-');
    }

    /*
     *  Event Handlers
     */

    $(function onDocReady() {
        $('#loginForm').submit(handleSignin);
        $('#registrationForm').submit(handleRegister);
        $('#verifyForm').submit(handleVerify);
    });

    function handleSignin(event) {
        // var email = $('#emailInputSignin').val();
        // var password = $('#passwordInputSignin').val();
        var email = $('#emailInputSignin').val();
        var password = $('#passwordInputSignin').val();
        event.preventDefault();
        signin(email, password,
            function signinSuccess() {
                console.log('Successfully Logged In');
                window.location.href = "http://54.144.11.150:3000/";
            },
            function signinError(err) {
                alert(err);
            }
        );
    }

    



    
    function handleRegister(event) {
        var email = $('#emailInputRegister').val();
        var password = $('#passwordInputRegister').val();
        var password2 = $('#password2InputRegister').val();

        var onSuccess = function registerSuccess(result) {
            var cognitoUser = result.user;
            console.log('user name is ' + cognitoUser.getUsername());
            var confirmation = ('Registration successful. Please check your email inbox or spam folder for your verification code.');
            if (confirmation) {
                window.location.href = 'verify.html';
            }
        };
        var onFailure = function registerFailure(err) {
            alert(err);
        };
        event.preventDefault();

        if (password === password2) {
            register(email, password, onSuccess, onFailure);
        } else {
            alert('Passwords do not match');
        }
    }

    function handleVerify(event) {
        var email = $('#emailInputVerify').val();
        var code = $('#codeInputVerify').val();
        event.preventDefault();
        verify(email, code,
            function verifySuccess(result) {
                console.log('call result: ' + result);
                console.log('Successfully verified');
                alert('Verification successful. You will now be redirected to the login page.');
                window.location.href = 'signin.html';
            },
            function verifyError(err) {
                alert(err);
            }
        );
    }
}(jQuery));



/*global WildRydes _config AmazonCognitoIdentity AWSCognito*/
/*global WildRydes _config AmazonCognitoIdentity AWSCognito*/

// var WildRydes = window.WildRydes || {};

// (function scopeWrapper($) {
//     var signinUrl = '/dev_signin.html';

//     var poolData = {
//         UserPoolId: _config.cognito.userPoolId,
//         ClientId: _config.cognito.userPoolClientId
//     };

//     var userPool;

//     if (!(_config.cognito.userPoolId &&
//           _config.cognito.userPoolClientId &&
//           _config.cognito.region)) {
//         $('#noCognitoMessage').show();
//         return;
//     }

//     userPool = new AmazonCognitoIdentity.CognitoUserPool(poolData);

//     if (typeof AWSCognito !== 'undefined') {
//         AWSCognito.config.region = _config.cognito.region;
//     }

//     WildRydes.signOut = function signOut() {
//         userPool.getCurrentUser().signOut();
//     };

//     WildRydes.authToken = new Promise(function fetchCurrentAuthToken(resolve, reject) {
//         var cognitoUser = userPool.getCurrentUser();

//         if (cognitoUser) {
//             cognitoUser.getSession(function sessionCallback(err, session) {
//                 if (err) {
//                     reject(err);
//                 } else if (!session.isValid()) {
//                     resolve(null);
//                 } else {
//                     resolve(session.getIdToken().getJwtToken());
//                 }
//             });
//         } else {
//             resolve(null);
//         }
//     });


//     /*
//      * Cognito User Pool functions
//      */

//     function register(email, password, onSuccess, onFailure) {
//         document.cookie = email;
//         var dataEmail = {
//             Name: 'email',
//             Value: email
//         };

//         console.log(dataEmail);
//         var attributeEmail = new AmazonCognitoIdentity.CognitoUserAttribute(dataEmail);

//         userPool.signUp(toUsername(email), password, [attributeEmail], null,
//             function signUpCallback(err, result) {
//                 if (!err) {
//                     onSuccess(result);
//                 } else {
//                     onFailure(err);
//                 }
//             }
//         );
//     }

//     function signin(email, password, onSuccess, onFailure) {
//         document.cookie = email;
//         var authenticationDetails = new AmazonCognitoIdentity.AuthenticationDetails({
//             Username: toUsername(email),
//             Password: password
//         });
//         var cognitoUser = createCognitoUser(email);
//         cognitoUser.authenticateUser(authenticationDetails, {
//             onSuccess: onSuccess,
//             onFailure: onFailure
//         });
//     }

//     function verify(email, code, onSuccess, onFailure) {
//         document.cookie = email;
//         createCognitoUser(email).confirmRegistration(code, true, function confirmCallback(err, result) {
//             if (!err) {
//                 onSuccess(result);
//             } else {
//                 onFailure(err);
//             }
//         });
//     }

//     function createCognitoUser(email) {
//         return new AmazonCognitoIdentity.CognitoUser({
//             Username: toUsername(email),
//             Pool: userPool
//         });
//     }

//     function toUsername(email) {
//         return email.replace('@', '-at-');
//     }

//     /*
//      *  Event Handlers
//      */

//     $(function onDocReady() {
//         $('#loginForm').submit(handleSignin);
//         $('#registrationForm').submit(handleRegister);
//         $('#verifyForm').submit(handleVerify);
//     });

//     function handleSignin(event) {
//         // var email = $('#emailInputSignin').val();
//         // var password = $('#passwordInputSignin').val();
//         var email = $('#emailInputSignin').val();
//         var password = $('#passwordInputSignin').val();
//         event.preventDefault();
//         signin(email, password,
//             function signinSuccess() {
//                 console.log('Successfully Logged In');
//                 window.location.href = 'Frontend/chat.html';
//             },
//             function signinError(err) {
//                 alert(err);
//             }
//         );
//     }

//     function handleRegister(event) {
//         var email = $('#emailInputRegister').val();
//         var password = $('#passwordInputRegister').val();
//         var password2 = $('#password2InputRegister').val();

//         var onSuccess = function registerSuccess(result) {
//             var cognitoUser = result.user;
//             console.log('user name is ' + cognitoUser.getUsername());
//             var confirmation = ('Registration successful. Please check your email inbox or spam folder for your verification code.');
//             if (confirmation) {
//                 window.location.href = 'dev-verify.html';
//             }
//         };
//         var onFailure = function registerFailure(err) {
//             alert(err);
//         };
//         event.preventDefault();

//         if (password === password2) {
//             register(email, password, onSuccess, onFailure);
//         } else {
//             alert('Passwords do not match');
//         }
//     }

//     function handleVerify(event) {
//         var email = $('#emailInputVerify').val();
//         var code = $('#codeInputVerify').val();
//         event.preventDefault();
//         verify(email, code,
//             function verifySuccess(result) {
//                 console.log('call result: ' + result);
//                 console.log('Successfully verified');
//                 alert('Verification successful. You will now be redirected to the login page.');
//                 window.location.href = 'dev_signin.html';
//             },
//             function verifyError(err) {
//                 alert(err);
//             }
//         );
//     }
// }(jQuery));


/*global WildRydes _config AmazonCognitoIdentity AWSCognito*/

// var WildRydes = window.WildRydes || {};

// (function scopeWrapper($) {
//     var signinUrl = '/signin.html';

//     var poolData = {
//         UserPoolId: _config.cognito.userPoolId,
//         ClientId: _config.cognito.userPoolClientId
//     };

//     var userPool;

//     if (!(_config.cognito.userPoolId &&
//           _config.cognito.userPoolClientId &&
//           _config.cognito.region)) {
//         $('#noCognitoMessage').show();
//         return;
//     }

//     userPool = new AmazonCognitoIdentity.CognitoUserPool(poolData);

//     if (typeof AWSCognito !== 'undefined') {
//         AWSCognito.config.region = _config.cognito.region;
//     }

//     WildRydes.signOut = function signOut() {
//         userPool.getCurrentUser().signOut();
//     };

//     WildRydes.authToken = new Promise(function fetchCurrentAuthToken(resolve, reject) {
//         var cognitoUser = userPool.getCurrentUser();

//         if (cognitoUser) {
//             cognitoUser.getSession(function sessionCallback(err, session) {
//                 if (err) {
//                     reject(err);
//                 } else if (!session.isValid()) {
//                     resolve(null);
//                 } else {
//                     resolve(session.getIdToken().getJwtToken());
//                 }
//             });
//         } else {
//             resolve(null);
//         }
//     });


//     /*
//      * Cognito User Pool functions
//      */

//     function register(email, password, onSuccess, onFailure) {
//         var dataEmail = {
//             Name: 'email',
//             Value: email
//         };
//         console.log(dataEmail);
//         var attributeEmail = new AmazonCognitoIdentity.CognitoUserAttribute(dataEmail);

//         userPool.signUp(toUsername(email), password, [attributeEmail], null,
//             function signUpCallback(err, result) {
//                 if (!err) {
//                     onSuccess(result);
//                 } else {
//                     onFailure(err);
//                 }
//             }
//         );
//     }

//     function signin(email, password, onSuccess, onFailure) {
//         var authenticationDetails = new AmazonCognitoIdentity.AuthenticationDetails({
//             Username: toUsername(email),
//             Password: password
//         });

//         var cognitoUser = createCognitoUser(email);
//         cognitoUser.authenticateUser(authenticationDetails, {
//             onSuccess: onSuccess,
//             onFailure: onFailure
//         });
//     }

//     function verify(email, code, onSuccess, onFailure) {
//         createCognitoUser(email).confirmRegistration(code, true, function confirmCallback(err, result) {
//             if (!err) {
//                 onSuccess(result);
//             } else {
//                 onFailure(err);
//             }
//         });
//     }

//     function createCognitoUser(email) {
//         return new AmazonCognitoIdentity.CognitoUser({
//             Username: toUsername(email),
//             Pool: userPool
//         });
//     }

//     function toUsername(email) {
//         return email.replace('@', '-at-');
//     }

//     /*
//      *  Event Handlers
//      */

//     $(function onDocReady() {
//         $('#devloginForm').submit(handleSignin);
//         $('#registrationForm').submit(handleRegister);
//         $('#verifyForm').submit(handleVerify);
//     });

//     function handleSignin(event) {
//         var email = $('#emailInputSignin').val();
//         var password = $('#passwordInputSignin').val();
//         // var email = $('#emailInputSignin').val();
//         // var password = $('#passwordInputSignin').val();
//         event.preventDefault();
//         signin(email, password,
//             function signinSuccess() {
//                 console.log('Successfully Logged In');
//                 window.location.href = 'http://54.144.11.150:3000/';
//             },
//             function signinError(err) {
//                 alert(err);
//             }
//         );
//     }


    





//     // function handleSignin(event) {
//     //     const email = document.getElementById('email').value;
//     // const password = document.getElementById('password').value;

//     // const authenticationData = {
//     //     Username: email,
//     //     Password: password,
//     // };
//     // const authenticationDetails = new AWS.CognitoIdentityServiceProvider.AuthenticationDetails(authenticationData);

//     // const userData = {
//     //     Username: email,
//     //     Pool: userPool
//     // };
//     // const cognitoUser = new AWS.CognitoIdentityServiceProvider.CognitoUser(userData);

//     // cognitoUser.authenticateUser(authenticationDetails, {
//     //     onSuccess: function (result) {
//     //         console.log('Authentication successful!');
//     //         window.location.href = 'http://54.144.11.150:3000/'; // Redirect to Grafana
//     //     },
//     //     onFailure: function(err) {
//     //         console.error('Authentication failed: ', err);
//     //         alert('Authentication failed: ' + err.message || JSON.stringify(err));
//     //     }
//     // });
//     // }

//     function handleRegister(event) {
//         var email = $('#emailInputRegister').val();
//         var password = $('#passwordInputRegister').val();
//         var password2 = $('#password2InputRegister').val();

//         var onSuccess = function registerSuccess(result) {
//             var cognitoUser = result.user;
//             console.log('user name is ' + cognitoUser.getUsername());
//             var confirmation = ('Registration successful. Please check your email inbox or spam folder for your verification code.');
//             if (confirmation) {
//                 window.location.href = 'verify.html';
//             }
//         };
//         var onFailure = function registerFailure(err) {
//             alert(err);
//         };
//         event.preventDefault();

//         if (password === password2) {
//             register(email, password, onSuccess, onFailure);
//         } else {
//             alert('Passwords do not match');
//         }
//     }

//     function handleVerify(event) {
//         var email = $('#emailInputVerify').val();
//         var code = $('#codeInputVerify').val();
//         event.preventDefault();
//         verify(email, code,
//             function verifySuccess(result) {
//                 console.log('call result: ' + result);
//                 console.log('Successfully verified');
//                 alert('Verification successful. You will now be redirected to the login page.');
//                 window.location.href = 'signin.html';
//             },
//             function verifyError(err) {
//                 alert(err);
//             }
//         );
//     }
// }(jQuery));

