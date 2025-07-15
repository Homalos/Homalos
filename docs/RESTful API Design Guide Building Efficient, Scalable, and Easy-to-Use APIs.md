# RESTful API设计指南：构建高效、可扩展和易用的API

## 文章目录

- 引言
- 一、RESTful API概述
  - 1.1 什么是RESTful API
  - 1.2 RESTful API的重要性
- 二、RESTful API的基本原则
  - 2.1 资源导向设计
  - 2.2 HTTP方法的正确使用
- 三、URL设计
  - 3.1 使用名词而非动词
  - 3.2 使用复数形式表示资源集合
- 四、请求和响应设计
  - 4.1 HTTP状态码
  - 4.2 响应格式
  - - 4.2.1 响应实体信息
    - 4.2.2 响应列表格式
    - 4.2.3 响应分页格式
  - 4.3 使用 HATEOAS 导航到相关资源
  - 4.4 错误处理
- 五、URI 版本管理
  - 5.1 常见的版本控制策略
  - 5.2 如何选择
- 六、数据筛选和分页
  - 6.1 分页和过滤
- 七、文档
- 八、安全性
- 总结

---

## 引言

在当今互联网时代，应用程序和服务之间的通信变得越来越重要。随着移动设备的普及、云计算的发展以及物联网的兴起，我们需要一种灵活、高效且易于理解的方式来设计和实现这些通信接口。RESTful API应运而生，成为了现代软件架构中不可或缺的一部分。

## 一、RESTful API概述

### 1.1 什么是RESTful API

RESTful API（Representational State Transfer API），中文翻译过来可以表述为表述性状态转移，是一种基于HTTP协议的网络应用程序接口风格。它遵循REST架构风格的约束条件和原则，以资源为中心，使用标准的HTTP方法（如GET、POST、PUT、DELETE等）来执行操作。RESTful API强调简单性、可扩展性和可读性，使得不同系统之间的通信变得更加直观和高效。

### 1.2 RESTful API的重要性

RESTful API在现代软件开发中扮演着关键角色，其重要性体现在以下几个方面：

1. 标准化：RESTful API遵循统一的设计原则，使得不同开发团队和系统之间的集成变得更加容易。
2. 可扩展性：基于资源的设计使得API能够轻松地适应新的需求和功能扩展。
3. 简单易用：RESTful API的设计理念使得接口更加直观，降低了开发者的学习成本。

本文旨在提供一个RESTful API设计指南，帮助开发人员构建高效、可扩展和易用的API。我们将介绍RESTful API设计的原则、最佳实践和模式，并提供一些实用的技巧和示例。通过遵循这些指南，开发人员可以设计出易于理解、易于使用和易于维护的API。

## 二、RESTful API的基本原则

### 2.1 资源导向设计

资源是RESTful API的核心概念。每个资源都应该有一个唯一的标识符（通常是URL）。设计API时，应该围绕资源而不是动作来组织。例如，一个用户资源可能表示为 `/users/{id}`。

### 2.2 HTTP方法的正确使用

RESTful API利用HTTP方法来表示对资源的操作，常用的有下面几种：

- GET(SELECT)：获取资源
- POST(CREATE)：创建新资源
- PUT(UPDATE)：更新现有资源
- DELETE(DELETE)：删除资源
- PATCH(UPDATE)：在服务器更新资源（客户端提供改变的属性）。

范例：

```reStructuredText
GET /users  // 获取用户列表
POST /users  // 创建新用户
PUT /users/{userId} //获取指定ID的用户信息
PUT /users/{userId}  // 更新指定ID的用户信息
DELETE /users/{userId}  // 删除指定ID的用户
PATCH /users/{userId}  // 更新指定ID用户的部分信息
```

除此之外还有两种：

- HEAD：获取资源的元数据。
- OPTIONS：获取信息，关于资源的哪些属性是客户端可以改变的。

## 三、URL设计

### 3.1 参数命名规范

query parameter 采用驼峰或下划线都可以

```reStructuredText
https://example.com/api/users/today_login  获取今天登录的用户
https://example.com/api/users/today_login&sort=login_desc  获取今天登录的用户并以降序排列
```

URL应该表示资源，而不是动作。使用HTTP方法来表示动作。

### 3.2 使用名词而非动词

API命名应该按照约定俗成的方式，简洁明了。在RESTful架构中，每个URL代表一种资源所以URL中不能有动词，只能有名词，并且名词中也应该使用复数。实现者应使用相应的HTTP动词GET、POST、PUT、PATCH、DELETE、HEAD来操作这些资源即可。

URL应该表示资源，而不是动作。使用HTTP方法来表示动作。

范例：

- GET /users
- GET /api/users
- GET /users/1
- DELETE /users/1
- PATCH /users/1
- POST /users

避免：

- GET /getallUsers
- POST /createUser
- GET /getuser/1
- GET/POST /user/delete/1
- POST /updateUser/1
- POST /User/add

### 3.3 使用复数形式表示资源集合

对于资源集合，使用复数形式更为直观。

范例：

- GET /users
- GET /users/{id}

避免：

- GET /user
- GET /user/{id}

## 四、请求和响应设计

### 4.1 HTTP状态码

> HTTP状态码是表示请求结果的标准方式，正确使用状态码可以提高API的可读性和一致性，根据HTTP status code就可以知道删除、添加、修改等是否成功。

HTTP状态码范围：

| 分类  | 分类描述                                                     |
| ----- | ------------------------------------------------------------ |
| `1**` | 信息，服务器收到请求，需要请求者继续执行操作                 |
| `2**` | 成功，操作被成功接收并处理                                   |
| `3**` | 重定向，需要进一步的操作以完成请求                           |
| `4**` | 客户端错误，请求包含语法错误或无法完成请求                   |
| `5**` | 服务器错误，服务器在处理请求的过程中发生了错误，这些错误可能是服务器本身出错，而不是请求出错 |

常用状态码：

```reStructuredText
200 OK - [GET]：服务器成功返回用户请求的数据，该操作是幂等的（Idempotent）。
201 CREATED - [POST/PUT/PATCH]：用户新建或修改数据成功。
202 Accepted - [*]：表示一个请求已经进入后台排队（异步任务）
204 NO CONTENT - [DELETE]：用户删除数据成功。
400 INVALID REQUEST - [POST/PUT/PATCH]：
        用户发出的请求有错误，服务器没有进行新建或修改数据的操作，该操作是幂等的。
401 Unauthorized - [*]：表示用户没有权限（令牌、用户名、密码错误）。
403 Forbidden - [*] 表示用户得到授权（与401错误相对），但是访问是被禁止的。
404 NOT FOUND - [*]：用户发出的请求针对的是不存在的记录，服务器没有进行操作，该操作是幂等的。
406 Not Acceptable - [GET]：用户请求的格式不可得（比如用户请求JSON格式，但是只有XML格式）。
410 Gone -[GET]：用户请求的资源被永久删除，且不会再得到的。
422 Unprocesable entity - [POST/PUT/PATCH] 当创建一个对象时，发生一个验证错误。
500 INTERNAL SERVER ERROR - [*]：服务器发生错误，用户将无法判断发出的请求是否成功。
502 Bad Gateway - [*]：服务器作为网关或代理，从上游服务器收到无效响应。
503 Service Unavailable - [*]：服务器当前无法处理请求，可能是由于过载或维护。
504 Gateway Timeout - [*]：服务器作为网关或代理，没有及时从上游服务器收到响应。
```

根据具体情况选择适当的状态码，避免滥用200状态码来表示所有情况。

### 4.2 响应格式

> 请求响应传输数据格式：JSON，JSON数据尽量简单轻量，避免多级JSON的出现。

#### 4.2.1 统一返回数据格式

对于合法的请求应该统一返回数据格式，以json为例：

- code：包含一个证书类型的HTTP相应的状态码
- status：包含文本：“success”,"fail"或“error”。
  - 状态码在500-599为“fail”
  - 状态码在400-499为“error”
  - 其余均为“success”
- message：当状态值为“fail”和“error”时有效，用于显示错误信息。参照国际化标准，他可以包含信息码或者编码。
- data：包含响应的body。当状态值为“fail”和“error”时，data仅包含错误原因或异常名称、或者null。

#### 4.2.2 响应实体信息

##### 4.2.2.1 成功返回的响应格式

```json
{
  code: 200,
  msg: "success",
  data: {
    entity: {
      id: 1,
      name: "XXX",
      code: "XXX"
    }
  }
}
```

##### 4.2.2.2 失败返回的响应格式

```json
{
    "code": 401,
    "message": "error message",
    "data": null
}
```

#### 4.2.3 响应列表格式

```json
{
  code: 200,
  msg: "success",
  data: {
    records: {
      entity: {
        id: 1,
        name: "XXX",
        code: "XXX"
      },
      entity: {
        id: 2,
        name: "XXX",
        code: "XXX"
      }
    }
  }
}
```

#### 4.2.4 响应分页格式

```json
{
  "msg": "success",
  "code": 200,
  "data": {
    "current": 0,
    "records": [{
        id: 1,
        name: "XXX",
        code: "H001"
      },
      {
        id: 2,
        name: "XXX",
        code: "H001"
      }
    ],
    "size": 5,
    "total": 2
  }
}
```

> 分析：
>
> data: 数据主体，包含了分页信息和记录列表。
> current: 当前页码，这里的值为 0，表示第一页（具体按照公司规范）。
> records: 记录列表，包含了当前页的所有记录，每个记录包含 id、name 和 code 字段。
> size: 每页大小，这里的值为 5，表示每页最多显示5条记录。
> total: 总记录数，这里的值为 2，表示一共有2条记录。

### 4.3 使用 HATEOAS 导航到相关资源

> REST 背后的主要动机之一是它应能够导航整个资源集，而无需事先了解 URI 方案。 每个 HTTP GET 请求应通过响应中包含的超链接返回查找与所请求的对象直接相关的资源所需的信息，还应为它提供描述其中每个资源提供的操作的信息。 此原则称为 HATEOAS 或作为应用程序状态引擎的超文本。
>
> 由于当前没有如何为 HATEOAS 原则建模的任何通用标准，因此此部分的示例仅作为一个可能的参考。
>

例如，若要处理订单与客户之间的关系，可以在订单的表示形式中包含链接，用于指定下单客户可以执行的操作。 下面是可能的表示形式：

```json
{
  "orderID":3,
  "productID":2,
  "quantity":4,
  "orderValue":16.60,
  "links":[
    {
      "rel":"customer",
      "href":"https://adventure-works.com/customers/3",
      "action":"GET",
      "types":["text/xml","application/json"]
    },
    {
      "rel":"customer",
      "href":"https://adventure-works.com/customers/3",
      "action":"PUT",
      "types":["application/x-www-form-urlencoded"]
    },
    {
      "rel":"customer",
      "href":"https://adventure-works.com/customers/3",
      "action":"DELETE",
      "types":[]
    },
    {
      "rel":"self",
      "href":"https://adventure-works.com/orders/3",
      "action":"GET",
      "types":["text/xml","application/json"]
    }
  ]
}
```

> 在此示例中，links 数组包含一组链接。 每个链接表示可对相关实体执行的操作。 每个链接的数据包含关系 (“customer”)、URI (<https://adventure-works.com/customers/3)、HTTP> 方法和支持的 MIME 类型。 这是客户端应用程序在调用操作时所需的全部信息。
>
> links 数组还包含有关已检索的资源本身的自引用信息。 这些链接包含关系 self。
>

### 4.4 错误处理

错误处理通常是 API 的弱点。清晰地传达问题，有助于开发者更容易找出问题的根源。像“400 Bad Request: 缺少 ‘order_id’”这样的具体消息有助于更顺利的排查问题。

错误响应应包含：

- HTTP状态码
- 错误消息
- 错误代码（可选）
- 详细说明（可选）

例如：

```json
{
    "code": "50x",
    "message": "The provided email address is invalid"
}
```

## 五、URI 版本管理

在构建出一个优秀的 API 后，更新和修复是不可避免的。版本控制有助于在不影响现有用户的情况下引入新特性。明确显示版本（例如 `/v1/users`），确保每个版本始终如一地工作。

### 5.1 常见的版本控制策略

1. URI 路径版本控制

   例如：`/api/v1/users`

2. 查询参数版本控制

   例如：`/api/users?version=1`

3. 自定义 HTTP 头版本控制

   例如：`Accept-version: v1`

4. Accept 头版本控制

   例如：`Accept: application/vnd.myapp.v1+json`

### 5.2 如何选择

选择版本控制策略时，还应考虑对性能的影响，尤其是在 Web 服务器上缓存时。 URI 路径版本控制和查询参数版本控制方案都是缓存友好的，因为同一 URI/查询字符串组合每次都指向相同的数据。

自定义 HTTP 头版本控制和Accept 头版本控制机制通常需要其他逻辑来检查自定义标头或 Accept 标头中的值。 在大型环境中，使用不同版本的 Web API 的多个客户端可能会在服务器端缓存中生成大量重复数据。 如果客户端应用程序通过实现缓存的代理与 Web 服务器进行通信，并且该代理在当前未在其缓存中保留所请求数据的副本时，仅将请求转发到 Web 服务器，则此问题可能会变得很严重。

## 六、数据筛选和分页

### 6.1 分页和过滤

> 在请求数据时，客户端经常对数据进行分页和过滤等要求，而这些参数推荐采用HTTP Query Parameter的方式实现
>
> 对集合资源执行的 GET 请求可能返回大量的项。 应将 Web API 设计为限制任何单个请求返回的数据量。 请考虑支持查询字符串指定要检索的最大项数和集合中的起始偏移量。

- 分页：
  - 使用 limit 和 offset 参数
  - 或者使用基于游标的分页
- 过滤：
  - 允许客户端指定过滤条件
  - 使用查询参数进行过滤

```reStructuredText
?limit=10：指定返回记录的数量
?offset=10：指定返回记录的开始位置。
/users?page=2&per_page=100&status=active：指定第几页，以及每页的记录数，相应数据的状态。
/users?sortby=name&order=asc：指定返回结果按照哪个属性排序，以及排序顺序。
/animals?animal_type_id=1：指定筛选条件
/users?recently_login_day=3：最近登陆的所有用户
/users?q=key&sort=create_title_asc,liveness_desc：搜索用户，并按照注册时间升序、活跃度降序
/blogs/{blogApp}/posts?pageIndex={pageIndex}：获取个人博客随笔列表，blogApp：博客名
```

## 七、文档

API 文档就像用户手册。涵盖必要的信息，如端点描述、请求/响应格式和示例错误消息。像 Swagger 和 Apipost 这样的工具帮助创建互动式文档，使其更加用户友好并像教程一样易于理解。

## 八、安全性

由于 API 经常处理敏感数据，因此安全性至关重要。使用 SSL/TLS 加密，实施像 OAuth2 这样的安全认证方法，并防范 SQL 注入等攻击。这些措施可以保护 API 和其用户的安全。

## 总结

一个设计良好的 API 使开发人员能够顺利使用它。遵循这些指南可以让你的 API 更具吸引力并广泛被采用。
